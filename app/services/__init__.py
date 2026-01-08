"""服务模块初始化"""
from .datasource import DataSource
from .akshare_datasource import AkshareDataSource
from .tushare_datasource import TushareDataSource
from .datasource_factory import DataSourceFactory, get_datasource
from .stock_service import StockService, get_stock_service
from .market_data_service import MarketDataService, get_market_data_service
from .strategy_service import StrategyService, get_strategy_service
from .strategy_executor import StrategyExecutor, get_strategy_executor
from .stock_date_range_service import StockDateRangeService

# 单例缓存
_stock_date_range_service_instance = None

def get_stock_date_range_service():
    """
    获取股票日期范围服务单例
    
    Returns:
        StockDateRangeService: 日期范围服务实例
    """
    global _stock_date_range_service_instance
    
    if _stock_date_range_service_instance is None:
        from app.models.mysql_db import get_mysql_db
        database = get_mysql_db()
        _stock_date_range_service_instance = StockDateRangeService(database)
    
    return _stock_date_range_service_instance
__all__ = [
    'DataSource',
    'AkshareDataSource',
    'TushareDataSource',
    'DataSourceFactory',
    'get_datasource',
    'StockService',
    'get_stock_service',
    'MarketDataService',
    'get_market_data_service',
    'StrategyService',
    'get_strategy_service',
    'StrategyExecutor',
    'get_strategy_executor',
    'StockDateRangeService',
    'get_stock_date_range_service'
]