"""
数据库操作重试装饰器
"""
import time
from functools import wraps
from typing import Callable, Any, Type, Tuple
from app.utils import get_logger

logger = get_logger(__name__)


def retry_db_operation(
    max_retries: int = 3,
    retry_delay: float = 0.5,
    backoff_factor: float = 2.0,
    retry_exceptions: Tuple[Type[Exception], ...] = None
):
    """
    数据库操作重试装饰器
    
    Args:
        max_retries: 最大重试次数（默认 3 次）
        retry_delay: 初始重试延迟（秒，默认 0.5 秒）
        backoff_factor: 退避因子（默认 2.0，每次重试延迟时间翻倍）
        retry_exceptions: 需要重试的异常类型（默认所有异常都重试）
        
    Returns:
        装饰器函数
        
    Example:
        @retry_db_operation(max_retries=3, retry_delay=0.5)
        def execute_query(self, query: str, params: tuple = None) -> list:
            # 数据库操作
            pass
    """
    if retry_exceptions is None:
        # 默认重试这些常见数据库异常
        from pymysql import OperationalError, InterfaceError, DatabaseError
        from sqlalchemy.exc import (
            OperationalError as SQLAlchemyOperationalError,
            InterfaceError as SQLAlchemyInterfaceError,
            DatabaseError as SQLAlchemyDatabaseError,
            DisconnectionError
        )
        retry_exceptions = (
            OperationalError,
            InterfaceError,
            DatabaseError,
            SQLAlchemyOperationalError,
            SQLAlchemyInterfaceError,
            SQLAlchemyDatabaseError,
            DisconnectionError
        )
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            current_delay = retry_delay
            
            for attempt in range(max_retries + 1):  # +1 表示包括第一次尝试
                try:
                    return func(*args, **kwargs)
                except retry_exceptions as e:
                    last_exception = e
                    
                    # 最后一次尝试失败，不再重试
                    if attempt >= max_retries:
                        error_msg = (
                            f"数据库操作失败，已达到最大重试次数 {max_retries}，"
                            f"函数: {func.__name__}，异常: {type(e).__name__}: {e}"
                        )
                        logger.error(error_msg)
                        raise
                    
                    # 记录重试日志
                    retry_msg = (
                        f"数据库操作失败，准备第 {attempt + 1}/{max_retries} 次重试，"
                        f"函数: {func.__name__}，"
                        f"异常: {type(e).__name__}: {e}，"
                        f"等待 {current_delay:.2f} 秒后重试..."
                    )
                    logger.warning(retry_msg)
                    
                    # 等待指定时间
                    time.sleep(current_delay)
                    
                    # 计算下次重试的延迟时间（指数退避）
                    current_delay *= backoff_factor
                    
                except Exception as e:
                    # 非数据库异常，不重试，直接抛出
                    logger.error(f"数据库操作遇到非预期异常，函数: {func.__name__}，异常: {type(e).__name__}: {e}")
                    raise
            
            # 理论上不会执行到这里，但为了类型检查
            if last_exception:
                raise last_exception
        
        return wrapper
    return decorator
