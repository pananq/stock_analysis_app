"""
API Token 管理服务
用于生成、验证和撤销长期 API Token
"""
import secrets
import threading
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import sessionmaker

from app.models.orm_models import ORMDatabase, ApiToken, User
from app.utils import get_logger, get_config
from app.utils.auth import AuthUtils

logger = get_logger(__name__)


class ApiTokenService:
    def __init__(self):
        config = get_config()
        mysql_config = config.get('database.mysql')
        if not mysql_config:
            raise ValueError("未配置MySQL数据库信息")

        mysql_url = (
            f"mysql+pymysql://{mysql_config.get('username')}:"
            f"{mysql_config.get('password')}@"
            f"{mysql_config.get('host')}:"
            f"{mysql_config.get('port')}/"
            f"{mysql_config.get('database')}?charset=utf8mb4"
        )

        self.orm_db = ORMDatabase(mysql_url)
        self.Session = sessionmaker(bind=self.orm_db.engine)
        logger.info("ApiTokenService初始化完成")

    def create_token(self, user_id: int, name: str) -> Dict[str, Any]:
        """
        创建新的 API Token

        Returns:
            {"success": True, "token": "sk-xxx", "prefix": "sk-ab12", "id": 1}
            明文 token 仅在此处返回一次
        """
        session = self.Session()
        try:
            raw_token = "sk-" + secrets.token_urlsafe(32)
            prefix = raw_token[:8]
            token_hash = AuthUtils.hash_password(raw_token)

            token = ApiToken(
                user_id=user_id,
                name=name,
                token_hash=token_hash,
                token_prefix=prefix,
                is_active=True
            )
            session.add(token)
            session.commit()

            return {
                'success': True,
                'token': raw_token,
                'prefix': prefix,
                'id': token.id
            }
        except Exception as e:
            session.rollback()
            logger.error(f"创建 API Token 失败: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            session.close()

    def verify_token(self, raw_token: str) -> Optional[Dict[str, Any]]:
        """
        验证 API Token

        Returns:
            {"user_id": int, "username": str} or None
        """
        if not raw_token or len(raw_token) < 8:
            return None

        prefix = raw_token[:8]
        session = self.Session()
        try:
            candidates = session.query(ApiToken).filter(
                ApiToken.token_prefix == prefix,
                ApiToken.is_active == True
            ).all()

            for token in candidates:
                if AuthUtils.verify_password(raw_token, token.token_hash):
                    # Update last_used_at
                    token.last_used_at = datetime.now()
                    # Get username
                    user = session.query(User).filter(User.id == token.user_id).first()
                    session.commit()
                    return {
                        'user_id': token.user_id,
                        'username': user.username if user else None
                    }

            return None
        except Exception as e:
            session.rollback()
            logger.error(f"验证 API Token 失败: {e}")
            return None
        finally:
            session.close()

    def revoke_token(self, user_id: int, token_id: int) -> bool:
        """撤销 API Token（软删除）"""
        session = self.Session()
        try:
            token = session.query(ApiToken).filter(
                ApiToken.id == token_id,
                ApiToken.user_id == user_id
            ).first()
            if not token:
                return False
            token.is_active = False
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"撤销 API Token 失败: {e}")
            return False
        finally:
            session.close()

    def list_tokens(self, user_id: int) -> List[Dict[str, Any]]:
        """列出用户的所有 API Token（不含 token_hash 和明文）"""
        session = self.Session()
        try:
            tokens = session.query(ApiToken).filter(
                ApiToken.user_id == user_id
            ).order_by(ApiToken.created_at.desc()).all()

            return [self._to_dict(t) for t in tokens]
        finally:
            session.close()

    def _to_dict(self, token: ApiToken) -> Dict[str, Any]:
        return {
            'id': token.id,
            'user_id': token.user_id,
            'name': token.name,
            'prefix': token.token_prefix,
            'is_active': token.is_active,
            'last_used_at': token.last_used_at.isoformat() if token.last_used_at else None,
            'created_at': token.created_at.isoformat() if token.created_at else None
        }
