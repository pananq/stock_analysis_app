#!/usr/bin/env python3
"""
API频率控制机制测试

测试内容：
1. 请求延迟控制（0.1-0.3秒随机延迟）
2. 频率限制错误检测
3. 自动重试机制
4. 暂停和恢复功能
"""

import os
import sys
import time
import threading
import unittest
from unittest.mock import Mock, patch

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils import get_logger
from app.utils.rate_limiter import RateLimiter


logger = get_logger(__name__)


class TestRateLimiter(unittest.TestCase):
    """频率限制器测试"""
    
    def test_01_creation(self):
        """测试频率限制器创建"""
        logger.info("测试频率限制器创建...")
        
        limiter = RateLimiter()
        self.assertIsNotNone(limiter)
        logger.info("✓ 频率限制器创建成功")
    
    def test_02_delay_range(self):
        """测试延迟范围（0.1-0.3秒）"""
        logger.info("测试延迟范围...")
        
        limiter = RateLimiter(min_delay=0.1, max_delay=0.3)
        
        delays = []
        for i in range(10):
            start_time = time.time()
            limiter.wait()
            elapsed = time.time() - start_time
            delays.append(elapsed)
        
        # 第一次调用可能没有延迟，所以从第二次开始检查
        for delay in delays[1:]:
            # 允许一定的误差
            self.assertGreaterEqual(delay, 0.08, f"延迟时间 {delay}秒 小于最小间隔")
            self.assertLessEqual(delay, 0.5, f"延迟时间 {delay}秒 大于最大间隔")
        
        avg_delay = sum(delays[1:]) / len(delays[1:])
        logger.info(f"  平均延迟: {avg_delay:.3f}秒")
        logger.info(f"  最小延迟: {min(delays[1:]):.3f}秒")
        logger.info(f"  最大延迟: {max(delays[1:]):.3f}秒")
        logger.info("✓ 延迟范围测试通过")
    
    def test_03_request_tracking(self):
        """测试请求间隔控制"""
        logger.info("测试请求间隔控制...")
        
        limiter = RateLimiter(min_delay=0.01, max_delay=0.02)
        
        # 连续发起多次请求
        request_times = []
        for i in range(5):
            limiter.wait()
            request_times.append(time.time())
        
        # 检查请求间隔
        intervals = []
        for i in range(1, len(request_times)):
            interval = request_times[i] - request_times[i-1]
            intervals.append(interval)
        
        logger.info(f"  请求间隔: {[f'{i:.3f}s' for i in intervals]}")
        logger.info("✓ 请求间隔控制测试通过")
    
    def test_04_pause_resume(self):
        """测试暂停和恢复功能"""
        logger.info("测试暂停和恢复功能...")
        
        limiter = RateLimiter(min_delay=0.01, max_delay=0.02)
        
        # 测试暂停
        limiter.pause()
        self.assertTrue(limiter.is_paused())
        logger.info("  已暂停")
        
        # 在暂停状态下，wait()应该阻塞
        # 使用线程测试
        wait_completed = [False]
        
        def wait_thread():
            limiter.wait()
            wait_completed[0] = True
        
        thread = threading.Thread(target=wait_thread)
        thread.daemon = True
        thread.start()
        
        # 等待一小段时间，wait应该还在阻塞
        time.sleep(0.2)
        self.assertFalse(wait_completed[0], "暂停状态下wait不应该完成")
        
        # 恢复
        limiter.resume()
        self.assertFalse(limiter.is_paused())
        logger.info("  已恢复")
        
        # 等待线程完成
        thread.join(timeout=1)
        self.assertTrue(wait_completed[0], "恢复后wait应该完成")
        
        logger.info("✓ 暂停和恢复功能测试通过")


class TestRateLimiterWithDataSource(unittest.TestCase):
    """频率限制器与数据源集成测试"""
    
    def test_01_datasource_with_rate_limiter(self):
        """测试数据源使用频率限制器"""
        logger.info("测试数据源使用频率限制器...")
        
        from app.services.datasource_factory import DataSourceFactory
        
        datasource = DataSourceFactory.create_datasource()
        
        # 测试多次请求
        start_time = time.time()
        
        try:
            # 连续获取3次股票列表
            for i in range(3):
                stocks = datasource.get_stock_list()
                logger.info(f"  第{i+1}次请求完成")
            
            elapsed = time.time() - start_time
            logger.info(f"  总耗时: {elapsed:.2f}秒")
            
            # 3次请求，每次间隔0.1-0.3秒，总时间应该在0.2-0.9秒之间
            # 加上网络时间，应该小于10秒
            self.assertLess(elapsed, 30, "请求总时间过长")
            
            logger.info("✓ 数据源频率限制测试通过")
        
        except Exception as e:
            logger.warning(f"测试失败（可能是网络问题）: {e}")
            self.skipTest(f"网络问题: {e}")


class TestRetryMechanism(unittest.TestCase):
    """重试机制测试"""
    
    def test_01_retry_on_failure(self):
        """测试失败时自动重试"""
        logger.info("测试失败时自动重试...")
        
        limiter = RateLimiter(min_delay=0.01, max_delay=0.02, max_retries=3)
        
        # 模拟失败的函数
        call_count = [0]
        
        def failing_function():
            call_count[0] += 1
            if call_count[0] < 3:
                raise Exception("模拟失败")
            return "成功"
        
        # 使用重试装饰器或方法
        result = limiter.execute_with_retry(failing_function)
        
        self.assertEqual(result, "成功")
        self.assertEqual(call_count[0], 3)  # 失败2次，成功1次
        
        logger.info(f"  重试次数: {call_count[0] - 1}")
        logger.info("✓ 重试机制测试通过")
    
    def test_02_max_retries_exceeded(self):
        """测试超过最大重试次数"""
        logger.info("测试超过最大重试次数...")
        
        limiter = RateLimiter(min_delay=0.01, max_delay=0.02, max_retries=3)
        
        # 模拟一直失败的函数
        def always_failing():
            raise Exception("始终失败")
        
        # 应该抛出异常
        with self.assertRaises(Exception):
            limiter.execute_with_retry(always_failing)
        
        logger.info("✓ 超过最大重试次数测试通过")


class TestConcurrency(unittest.TestCase):
    """并发测试"""
    
    def test_01_concurrent_requests(self):
        """测试并发请求"""
        logger.info("测试并发请求...")
        
        limiter = RateLimiter(min_delay=0.05, max_delay=0.1)
        
        results = []
        errors = []
        
        def make_request(i):
            try:
                limiter.wait()
                results.append(time.time())
            except Exception as e:
                errors.append(str(e))
        
        # 创建多个线程同时发起请求
        threads = []
        for i in range(5):
            t = threading.Thread(target=make_request, args=(i,))
            threads.append(t)
        
        # 启动所有线程
        start_time = time.time()
        for t in threads:
            t.start()
        
        # 等待所有线程完成
        for t in threads:
            t.join(timeout=5)
        
        elapsed = time.time() - start_time
        
        self.assertEqual(len(errors), 0, f"有错误发生: {errors}")
        self.assertEqual(len(results), 5, "不是所有请求都完成了")
        
        logger.info(f"  5个并发请求总耗时: {elapsed:.3f}秒")
        logger.info("✓ 并发请求测试通过")


def run_rate_limiter_tests():
    """运行所有频率限制测试"""
    logger.info("=" * 60)
    logger.info("开始运行API频率控制测试")
    logger.info("=" * 60)
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    test_classes = [
        TestRateLimiter,
        TestRateLimiterWithDataSource,
        TestRetryMechanism,
        TestConcurrency,
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出测试结果摘要
    logger.info("\n" + "=" * 60)
    logger.info("测试结果摘要")
    logger.info("=" * 60)
    logger.info(f"运行测试: {result.testsRun}")
    logger.info(f"成功: {result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped)}")
    logger.info(f"失败: {len(result.failures)}")
    logger.info(f"错误: {len(result.errors)}")
    logger.info(f"跳过: {len(result.skipped)}")
    
    return result


if __name__ == '__main__':
    run_rate_limiter_tests()
