from typing import Optional, Dict, Tuple
from datetime import datetime
from app.models.database_factory import get_database
from app.models.orm_models import User
from app.utils.auth import AuthUtils
from app.utils.logger import get_logger

logger = get_logger(__name__)

class AuthService:
    """认证服务类"""
    
    def __init__(self):
        self.db = get_database()
    
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
        
        session = self.db.get_session()
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
            
            user_info = {
                'id': new_user.id,
                'username': new_user.username,
                'role': new_user.role
            }
            
            return True, "注册成功", user_info
            
        except Exception as e:
            session.rollback()
            logger.error(f"注册失败: {e}")
            return False, f"注册失败: {str(e)}", None
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
        session = self.db.get_session()
        try:
            user = session.query(User).filter_by(username=username).first()
            
            if not user or not AuthUtils.verify_password(password, user.password_hash):
                return False, "用户名或密码错误", None, None
            
            # 更新最后登录时间
            user.last_login = datetime.now()
            session.commit()
            
            # 生成 Token
            token = AuthUtils.generate_token(user.id, user.username, user.role)
            
            user_info = {
                'id': user.id,
                'username': user.username,
                'role': user.role
            }
            
            return True, "登录成功", token, user_info
            
        except Exception as e:
            logger.error(f"登录失败: {e}")
            return False, f"登录失败: {str(e)}", None, None
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
        session = self.db.get_session()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            if user:
                return {
                    'id': user.id,
                    'username': user.username,
                    'role': user.role,
                    'created_at': user.created_at,
                    'last_login': user.last_login
                }
            return None
        finally:
            session.close()

    def ensure_admin_exists(self, default_password: str = 'admin123') -> bool:
        """
        确保管理员用户存在
        
        Args:
            default_password: 默认密码
            
        Returns:
            bool: 是否创建了新管理员
        """
        session = self.db.get_session()
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
                logger.info(f"默认管理员创建成功: admin / {default_password}")
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
        session = self.db.get_session()
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