"""服务模块初始化"""
import threading
from .datasource import DataSource
from .akshare_datasource import AkshareDataSource
from .tushare_datasource import TushareDataSource
from .datasource_factory import DataSourceFactory, get_datasource
from .stock_service import StockService, get_stock_service
from .market_data_service import MarketDataService, get_market_data_service
from .strategy_service import StrategyService, get_strategy_service
from .strategy_executor import StrategyExecutor, get_strategy_executor
from .stock_date_range_service import StockDateRangeService
from .watchlist_service import WatchlistService, get_watchlist_service
from .api_token_service import ApiTokenService
from .global_market_data_service import GlobalMarketDataService, get_global_market_data_service
from .security_list_service import SecurityListService
from .security_market_data_service import (
    SecurityMarketDataService,
    get_security_market_data_service,
)
from .analysis_service import MarketAnalysisService
from .ai_analysis_service import AIAnalysisService
from .email_service import EmailService
from .daily_report_service import DailyReportService, get_daily_report_service

# 单例缓存
_api_token_service_instance = None
_api_token_service_lock = threading.Lock()

def get_api_token_service() -> ApiTokenService:
    global _api_token_service_instance
    if _api_token_service_instance is None:
        with _api_token_service_lock:
            if _api_token_service_instance is None:
                _api_token_service_instance = ApiTokenService()
    return _api_token_service_instance


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
    'get_stock_date_range_service',
    'WatchlistService',
    'get_watchlist_service',
    'ApiTokenService',
    'get_api_token_service',
    'GlobalMarketDataService',
    'get_global_market_data_service',
    'SecurityListService',
    'SecurityMarketDataService',
    'get_security_market_data_service',
    'MarketAnalysisService',
    'AIAnalysisService',
    'EmailService',
    'DailyReportService',
    'get_daily_report_service',
]
