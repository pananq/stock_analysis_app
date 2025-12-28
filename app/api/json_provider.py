"""
自定义JSON Provider，用于格式化datetime对象
"""

from datetime import datetime, date
from flask.json.provider import DefaultJSONProvider


class CustomJSONProvider(DefaultJSONProvider):
    """自定义JSON提供者，格式化datetime和date对象"""
    
    def default(self, obj):
        """
        序列化对象
        
        Args:
            obj: 要序列化的对象
            
        Returns:
            序列化后的对象
        """
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        if isinstance(obj, date):
            return obj.strftime('%Y-%m-%d')
        return super().default(obj)
