"""工具模块初始化"""
from .config import ConfigManager, get_config
from .logger import LoggerManager, setup_logging, get_logger
from .rate_limiter import RateLimiter, get_rate_limiter, rate_limited

__all__ = [
    'ConfigManager',
    'get_config',
    'LoggerManager',
    'setup_logging',
    'get_logger',
    'RateLimiter',
    'get_rate_limiter',
    'rate_limited'
]


def is_development_mode() -> bool:
    """
    检查当前是否为开发模式

    Returns:
        如果是开发模式返回True，否则返回False
    """
    config = get_config()
    app_mode_config = config.get('app_mode', {})
    return app_mode_config.get('mode', 'production') == 'development'


def get_stock_limit_for_mode() -> int:
    """
    根据当前模式获取股票数量限制

    Returns:
        开发模式下返回限制数量，生产模式返回None（不限制）
    """
    if is_development_mode():
        config = get_config()
        app_mode_config = config.get('app_mode', {})
        return app_mode_config.get('development_stock_limit', 100)
    return None
