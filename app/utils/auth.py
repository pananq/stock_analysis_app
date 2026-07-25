import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Dict, Optional, Union
from app.utils.config import get_config
from app.utils.logger import get_logger

logger = get_logger(__name__)

class AuthUtils:
    """认证工具类"""

    @staticmethod
    def is_password_acceptable(password: str) -> bool:
        """新密码必须有合理长度，避免弱口令与异常超长输入。"""
        length = len(str(password or ''))
        return 12 <= length <= 128

    @staticmethod
    def is_secret_strong(secret_key: str) -> bool:
        """判断 JWT 密钥是否满足运行时最低安全要求。"""
        normalized = str(secret_key or '').strip()
        weak_markers = (
            'your-secret',
            'dev-secret',
            'change-me',
            'replace-with',
        )
        return (
            len(normalized) >= 32
            and not any(marker in normalized.lower() for marker in weak_markers)
        )

    @staticmethod
    def _get_secret_key() -> str:
        config = get_config()
        secret_key = config.get(
            'auth.secret_key',
            config.get('web.secret_key', '')
        )
        normalized = str(secret_key or '').strip()
        if not AuthUtils.is_secret_strong(normalized):
            raise ValueError(
                "AUTH_SECRET_KEY 未配置或强度不足，请设置至少 32 字符的随机密钥"
            )
        return normalized
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        生成密码哈希
        
        Args:
            password: 原始密码
            
        Returns:
            str: 哈希后的密码
        """
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """
        验证密码
        
        Args:
            password: 原始密码
            hashed: 哈希后的密码
            
        Returns:
            bool: 是否匹配
        """
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception as e:
            logger.error(f"密码验证失败: {e}")
            return False
    
    @staticmethod
    def generate_token(user_id: int, username: str, role: str, expires_in: int = 3600) -> str:
        """
        生成 JWT Token
        
        Args:
            user_id: 用户ID
            username: 用户名
            role: 角色
            expires_in: 过期时间（秒）
            
        Returns:
            str: JWT Token
        """
        config = get_config()
        secret_key = AuthUtils._get_secret_key()
        configured_hours = int(config.get('auth.token_expire_hours', 1))
        if expires_in == 3600:
            expires_in = configured_hours * 3600
        
        payload = {
            'user_id': user_id,
            'username': username,
            'role': role,
            'exp': datetime.utcnow() + timedelta(seconds=expires_in),
            'iat': datetime.utcnow()
        }
        
        token = jwt.encode(payload, secret_key, algorithm='HS256')
        return token
    
    @staticmethod
    def verify_token(token: str) -> Optional[Dict]:
        """
        验证 JWT Token
        
        Args:
            token: JWT Token
            
        Returns:
            Optional[Dict]: Token 载荷，验证失败返回 None
        """
        try:
            secret_key = AuthUtils._get_secret_key()
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            return payload
        except ValueError as e:
            logger.error(f"认证密钥配置无效: {e}")
            return None
        except jwt.ExpiredSignatureError:
            logger.warning("Token已过期")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"无效的Token: {e}")
            return None
