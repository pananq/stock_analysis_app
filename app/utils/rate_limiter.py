"""
API访问频率控制模块
实现请求队列和延迟控制，避免被数据源封禁
"""
import time
import random
import threading
from typing import Callable, Any
from functools import wraps
from app.utils import get_config, get_logger

logger = get_logger(__name__)


class RateLimiter:
    """API访问频率限制器"""
    
    def __init__(self, min_delay: float = 0.1, max_delay: float = 0.3, 
                 max_retries: int = 3, retry_delay_increment: float = 0.5):
        """
        初始化频率限制器
        
        Args:
            min_delay: 最小延迟时间（秒）
            max_delay: 最大延迟时间（秒）
            max_retries: 最大重试次数
            retry_delay_increment: 重试延迟增量（秒）
        """
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.max_retries = max_retries
        self.retry_delay_increment = retry_delay_increment
        self.last_request_time = 0
        self.lock = threading.Lock()
        self._paused = False
        self._pause_lock = threading.Lock()
        
        logger.info(f"频率限制器初始化: 延迟{min_delay}-{max_delay}秒, 最大重试{max_retries}次")
    
    def wait(self):
        """等待适当的时间间隔"""
        with self.lock:
            # 检查是否暂停
            while self._paused:
                time.sleep(0.1)
            
            # 计算需要等待的时间
            current_time = time.time()
            elapsed = current_time - self.last_request_time
            
            # 随机延迟
            delay = random.uniform(self.min_delay, self.max_delay)
            
            if elapsed < delay:
                wait_time = delay - elapsed
                logger.debug(f"等待{wait_time:.2f}秒...")
                time.sleep(wait_time)
            
            self.last_request_time = time.time()
    
    def pause(self):
        """暂停请求"""
        with self._pause_lock:
            self._paused = True
            logger.info("频率限制器已暂停")
    
    def resume(self):
        """恢复请求"""
        with self._pause_lock:
            self._paused = False
            logger.info("频率限制器已恢复")
    
    def is_paused(self) -> bool:
        """检查是否暂停"""
        with self._pause_lock:
            return self._paused
    
    def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """
        执行函数并在失败时重试
        
        Args:
            func: 要执行的函数
            *args: 函数参数
            **kwargs: 函数关键字参数
            
        Returns:
            函数执行结果
            
        Raises:
            最后一次执行的异常
        """
        last_exception = None
        retry_delay = self.max_delay
        
        for attempt in range(self.max_retries + 1):
            try:
                # 等待适当的时间间隔
                self.wait()
                
                # 执行函数
                result = func(*args, **kwargs)
                
                # 成功则返回结果
                if attempt > 0:
                    logger.info(f"重试成功（第{attempt}次重试）")
                return result
                
            except Exception as e:
                last_exception = e
                
                # 检查是否是频率限制错误
                error_msg = str(e).lower()
                is_rate_limit_error = any(keyword in error_msg for keyword in [
                    'rate limit', 'too many requests', '频率', '限制', '429', '最多访问'
                ])
                
                if is_rate_limit_error:
                    logger.warning(f"检测到频率限制错误: {e}")
                    # 增加延迟时间（更激进的延迟策略）
                    retry_delay += self.retry_delay_increment
                    # 延迟到更合理的时间范围（考虑到Tushare 50次/分钟的）
                    # 至少需要 60/50 = 1.2秒/次，加上缓冲，设置为2.5秒
                    self.max_delay = min(retry_delay, 2.5)  
                
                if attempt < self.max_retries:
                    logger.warning(f"执行失败，{retry_delay:.2f}秒后重试（第{attempt + 1}次重试）: {e}")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"执行失败，已达到最大重试次数: {e}")
        
        # 所有重试都失败，抛出最后一个异常
        raise last_exception


# 全局频率限制器实例
_rate_limiter_instance = None


def get_rate_limiter() -> RateLimiter:
    """
    获取全局频率限制器实例
    
    Returns:
        RateLimiter实例
    """
    global _rate_limiter_instance
    if _rate_limiter_instance is None:
        config = get_config()
        rate_limit_config = config.get('api_rate_limit', {})
        
        _rate_limiter_instance = RateLimiter(
            min_delay=rate_limit_config.get('min_delay', 0.1),
            max_delay=rate_limit_config.get('max_delay', 0.3),
            max_retries=rate_limit_config.get('max_retries', 3),
            retry_delay_increment=rate_limit_config.get('retry_delay_increment', 0.5)
        )
    
    return _rate_limiter_instance


def rate_limited(func: Callable) -> Callable:
    """
    频率限制装饰器
    
    Args:
        func: 要装饰的函数
        
    Returns:
        装饰后的函数
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        rate_limiter = get_rate_limiter()
        return rate_limiter.execute_with_retry(func, *args, **kwargs)
    
    return wrapper
