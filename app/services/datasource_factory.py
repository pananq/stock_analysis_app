"""
数据源工厂
根据配置创建对应的数据源实例
"""
from typing import Optional
from .datasource import DataSource
from .akshare_datasource import AkshareDataSource
from .tushare_datasource import TushareDataSource
from app.utils import get_config, get_logger

logger = get_logger(__name__)


class DataSourceFactory:
    """数据源工厂类"""
    
    _instance: Optional[DataSource] = None
    
    @classmethod
    def create_datasource(cls, datasource_type: str = None, **kwargs) -> DataSource:
        """
        创建数据源实例
        
        Args:
            datasource_type: 数据源类型（akshare或tushare）
            **kwargs: 额外参数（如tushare的token）
            
        Returns:
            DataSource实例
        """
        if datasource_type is None:
            config = get_config()
            datasource_type = config.get('datasource.type', 'akshare')
        
        datasource_type = datasource_type.lower()
        
        if datasource_type == 'akshare':
            logger.info("创建Akshare数据源")
            return AkshareDataSource()
        
        elif datasource_type == 'tushare':
            logger.info("创建Tushare数据源")
            token = kwargs.get('token')
            if not token:
                config = get_config()
                # 支持两种配置格式: datasource.tushare.token 或 datasource.tushare_token
                token = config.get('datasource.tushare.token') or config.get('datasource.tushare_token')
            
            if not token:
                raise ValueError("使用Tushare数据源时必须提供token")
            
            return TushareDataSource(token)
        
        else:
            raise ValueError(f"不支持的数据源类型: {datasource_type}")
    
    @classmethod
    def get_datasource(cls) -> DataSource:
        """
        获取全局数据源实例（单例模式）
        
        Returns:
            DataSource实例
        """
        if cls._instance is None:
            cls._instance = cls.create_datasource()
        return cls._instance
    
    @classmethod
    def reset_datasource(cls):
        """重置数据源实例"""
        cls._instance = None


def get_datasource() -> DataSource:
    """
    获取数据源实例的便捷函数
    
    Returns:
        DataSource实例
    """
    return DataSourceFactory.get_datasource()
