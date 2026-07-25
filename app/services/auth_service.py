import re
from typing import Optional, Dict, Tuple
from datetime import datetime
from app.models.database_factory import get_database
from app.models.orm_models import User
from app.utils.auth import AuthUtils
from app.utils.logger import get_logger

logger = get_logger(__name__)

class AuthService:
    """认证服务类"""

    EMAIL_PATTERN = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
    
    def __init__(self, db=None, session_factory=None):
        """
        Args:
            db: 生产环境数据库适配器；默认使用全局数据库工厂。
            session_factory: 测试或嵌入场景可注入 SQLAlchemy Session 工厂。
        """
        self.db = db
        self.Session = session_factory
        if self.db is None and self.Session is None:
            self.db = get_database()

    def _get_session(self):
        return self.Session() if self.Session is not None else self.db.get_session()

    @staticmethod
    def _serialize_user(user: User) -> Dict:
        return {
            'id': user.id,
            'username': user.username,
            'role': user.role,
            'nickname': user.nickname,
            'email': user.email,
            'daily_report_enabled': bool(user.daily_report_enabled),
            'created_at': user.created_at,
            'last_login': user.last_login,
        }
    
    def register(self, username: str, password: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        用户注册
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            Tuple[bool, str, Optional[Dict]]: (是否成功, 消息, 用户信息)
        """
        # 验证用户名格式（8-16个英文字母字符）
        if not (8 <= len(username) <= 16 and username.isalpha()):
            return False, "用户名必须是8-16个英文字母", None
        if not AuthUtils.is_password_acceptable(password):
            return False, "密码长度必须为12-128个字符", None
        
        session = self._get_session()
        try:
            # 检查用户名是否存在
            existing_user = session.query(User).filter_by(username=username).first()
            if existing_user:
                return False, "用户名已存在", None
            
            # 创建新用户
            hashed_password = AuthUtils.hash_password(password)
            new_user = User(
                username=username,
                password_hash=hashed_password,
                role='user',
                created_at=datetime.now()
            )
            
            session.add(new_user)
            session.commit()
            session.refresh(new_user)
            
            user_info = self._serialize_user(new_user)
            
            return True, "注册成功", user_info
            
        except Exception as e:
            session.rollback()
            logger.error(f"注册失败: {e}")
            return False, "注册服务暂不可用", None
        finally:
            session.close()
    
    def login(self, username: str, password: str) -> Tuple[bool, str, Optional[str], Optional[Dict]]:
        """
        用户登录
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            Tuple[bool, str, Optional[str], Optional[Dict]]: (是否成功, 消息, Token, 用户信息)
        """
        session = self._get_session()
        try:
            user = session.query(User).filter_by(username=username).first()
            
            if not user or not AuthUtils.verify_password(password, user.password_hash):
                return False, "用户名或密码错误", None, None
            
            # 更新最后登录时间
            user.last_login = datetime.now()
            session.commit()
            
            # 生成 Token
            token = AuthUtils.generate_token(user.id, user.username, user.role)
            
            user_info = self._serialize_user(user)
            
            return True, "登录成功", token, user_info
            
        except Exception as e:
            logger.error(f"登录失败: {e}")
            return False, "登录服务暂不可用", None, None
        finally:
            session.close()
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """
        根据ID获取用户信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            Optional[Dict]: 用户信息
        """
        session = self._get_session()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            if user:
                return self._serialize_user(user)
            return None
        finally:
            session.close()

    def update_profile(
        self,
        user_id: int,
        nickname: Optional[str],
        email: Optional[str],
        daily_report_enabled: Optional[bool] = None,
    ) -> Tuple[bool, str, Optional[Dict]]:
        """更新当前用户的昵称和日报收件邮箱。"""
        nickname = (nickname or '').strip() or None
        email = (email or '').strip().lower() or None

        if nickname and len(nickname) > 50:
            return False, "昵称不能超过50个字符", None
        if email and (
            len(email) > 254
            or '\r' in email
            or '\n' in email
            or not self.EMAIL_PATTERN.fullmatch(email)
        ):
            return False, "请输入有效的邮箱地址", None

        session = self._get_session()
        try:
            user = session.query(User).filter_by(id=int(user_id)).first()
            if not user:
                return False, "用户不存在", None
            if daily_report_enabled is None:
                daily_report_enabled = bool(user.daily_report_enabled)
            if daily_report_enabled and not email:
                return False, "请先配置有效邮箱，再开启邮件日报", None
            user.nickname = nickname
            user.email = email
            user.daily_report_enabled = bool(daily_report_enabled)
            user.updated_at = datetime.now()
            session.commit()
            session.refresh(user)
            return True, "个人资料已保存", self._serialize_user(user)
        except Exception as exc:
            session.rollback()
            logger.error("更新用户资料失败: %s", exc)
            return False, "个人资料保存失败", None
        finally:
            session.close()

    def list_report_recipients(self) -> list[Dict]:
        """返回所有用户的个人日报投递偏好。"""
        session = self._get_session()
        try:
            users = session.query(User).order_by(User.id).all()
            return [
                {
                    'user_id': user.id,
                    'email': user.email,
                    'enabled': bool(user.daily_report_enabled),
                }
                for user in users
            ]
        finally:
            session.close()

    def ensure_admin_exists(self, default_password: str = None) -> bool:
        """
        确保管理员用户存在
        
        Args:
            default_password: 默认密码
            
        Returns:
            bool: 是否创建了新管理员
        """
        if not default_password:
            logger.warning(
                "未配置初始管理员密码，跳过自动创建管理员；"
                "请设置 ADMIN_INITIAL_PASSWORD 后重新初始化"
            )
            return False
        if not AuthUtils.is_password_acceptable(default_password):
            logger.error("初始管理员密码强度不足，必须为12-128个字符")
            return False

        session = self._get_session()
        try:
            admin = session.query(User).filter_by(role='admin').first()
            if not admin:
                logger.info("未发现管理员用户，正在创建默认管理员...")
                hashed_password = AuthUtils.hash_password(default_password)
                new_admin = User(
                    username='admin',
                    password_hash=hashed_password,
                    role='admin',
                    created_at=datetime.now()
                )
                session.add(new_admin)
                session.commit()
                logger.info("默认管理员创建成功: admin（密码未写入日志）")
                return True
            return False
        except Exception as e:
            session.rollback()
            logger.error(f"检查/创建管理员失败: {e}")
            return False
        finally:
            session.close()

    def reset_admin_password(self, new_password: str) -> bool:
        """
        重置管理员密码
        
        Args:
            new_password: 新密码
            
        Returns:
            bool: 是否成功
        """
        if not AuthUtils.is_password_acceptable(new_password):
            logger.error("管理员新密码强度不足，必须为12-128个字符")
            return False

        session = self._get_session()
        try:
            admin = session.query(User).filter_by(role='admin').first()
            if not admin:
                logger.error("未找到管理员用户")
                return False
            
            hashed_password = AuthUtils.hash_password(new_password)
            admin.password_hash = hashed_password
            session.commit()
            logger.info("管理员密码重置成功")
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"重置管理员密码失败: {e}")
            return False
        finally:
            session.close()
