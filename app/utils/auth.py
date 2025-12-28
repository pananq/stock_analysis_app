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
        secret_key = config.get('web.secret_key', 'dev-secret-key')
        
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
        config = get_config()
        secret_key = config.get('web.secret_key', 'dev-secret-key')
        
        try:
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token已过期")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"无效的Token: {e}")
            return None
