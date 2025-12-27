#!/usr/bin/env python3
"""
综合测试运行脚本

运行所有测试套件，生成测试报告
"""

import os
import sys
import time
import unittest
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils import get_logger


logger = get_logger(__name__)


def run_all_tests():
    """运行所有测试"""
    logger.info("=" * 70)
    logger.info("股票分析系统 - 综合测试")
    logger.info("=" * 70)
    logger.info(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("")
    
    # 导入测试模块
    from tests.test_integration import run_integration_tests
    from tests.test_rate_limiter import run_rate_limiter_tests
    from tests.test_datasource import run_datasource_tests
    from tests.test_performance import run_performance_tests
    
    results = {}
    total_start_time = time.time()
    
    # 1. 集成测试
    logger.info("\n" + "=" * 70)
    logger.info("1. 端到端集成测试")
    logger.info("=" * 70)
    start_time = time.time()
    results['integration'] = run_integration_tests()
    logger.info(f"耗时: {time.time() - start_time:.2f}秒")
    
    # 2. 频率控制测试
    logger.info("\n" + "=" * 70)
    logger.info("2. API频率控制测试")
    logger.info("=" * 70)
    start_time = time.time()
    results['rate_limiter'] = run_rate_limiter_tests()
    logger.info(f"耗时: {time.time() - start_time:.2f}秒")
    
    # 3. 数据源测试
    logger.info("\n" + "=" * 70)
    logger.info("3. 数据源切换测试")
    logger.info("=" * 70)
    start_time = time.time()
    results['datasource'] = run_datasource_tests()
    logger.info(f"耗时: {time.time() - start_time:.2f}秒")
    
    # 4. 性能测试
    logger.info("\n" + "=" * 70)
    logger.info("4. 数据库性能测试")
    logger.info("=" * 70)
    start_time = time.time()
    results['performance'] = run_performance_tests()
    logger.info(f"耗时: {time.time() - start_time:.2f}秒")
    
    # 总结
    total_time = time.time() - total_start_time
    
    logger.info("\n" + "=" * 70)
    logger.info("测试总结")
    logger.info("=" * 70)
    
    total_tests = 0
    total_failures = 0
    total_errors = 0
    total_skipped = 0
    
    for name, result in results.items():
        tests = result.testsRun
        failures = len(result.failures)
        errors = len(result.errors)
        skipped = len(result.skipped)
        passed = tests - failures - errors - skipped
        
        total_tests += tests
        total_failures += failures
        total_errors += errors
        total_skipped += skipped
        
        status = "✓" if failures == 0 and errors == 0 else "✗"
        logger.info(f"  {status} {name}: {passed}/{tests} 通过 "
                   f"({failures} 失败, {errors} 错误, {skipped} 跳过)")
    
    logger.info("")
    logger.info(f"  总测试数: {total_tests}")
    logger.info(f"  通过: {total_tests - total_failures - total_errors - total_skipped}")
    logger.info(f"  失败: {total_failures}")
    logger.info(f"  错误: {total_errors}")
    logger.info(f"  跳过: {total_skipped}")
    logger.info(f"  总耗时: {total_time:.2f}秒")
    logger.info("")
    
    # 判断是否全部通过
    if total_failures == 0 and total_errors == 0:
        logger.info("✓ 所有测试通过!")
        return 0
    else:
        logger.error("✗ 部分测试失败!")
        return 1


def run_quick_tests():
    """运行快速测试（不包含网络请求）"""
    logger.info("=" * 70)
    logger.info("股票分析系统 - 快速测试")
    logger.info("=" * 70)
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 只添加本地测试
    from tests.test_integration import (
        TestDatabaseIntegration,
        TestTechnicalIndicators,
        TestAPIIntegration
    )
    from tests.test_rate_limiter import (
        TestRateLimiter,
        TestRetryMechanism
    )
    from tests.test_performance import (
        TestSQLitePerformance,
        TestDuckDBPerformance
    )
    
    test_classes = [
        TestDatabaseIntegration,
        TestTechnicalIndicators,
        TestAPIIntegration,
        TestRateLimiter,
        TestRetryMechanism,
        TestSQLitePerformance,
        TestDuckDBPerformance,
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    logger.info("\n" + "=" * 70)
    logger.info("快速测试结果")
    logger.info("=" * 70)
    logger.info(f"运行测试: {result.testsRun}")
    logger.info(f"成功: {result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped)}")
    logger.info(f"失败: {len(result.failures)}")
    logger.info(f"错误: {len(result.errors)}")
    logger.info(f"跳过: {len(result.skipped)}")
    
    return result


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='股票分析系统测试')
    parser.add_argument('--quick', action='store_true', help='只运行快速测试')
    parser.add_argument('--module', type=str, help='指定测试模块 (integration, rate_limiter, datasource, performance)')
    
    args = parser.parse_args()
    
    if args.quick:
        run_quick_tests()
    elif args.module:
        if args.module == 'integration':
            from tests.test_integration import run_integration_tests
            run_integration_tests()
        elif args.module == 'rate_limiter':
            from tests.test_rate_limiter import run_rate_limiter_tests
            run_rate_limiter_tests()
        elif args.module == 'datasource':
            from tests.test_datasource import run_datasource_tests
            run_datasource_tests()
        elif args.module == 'performance':
            from tests.test_performance import run_performance_tests
            run_performance_tests()
        else:
            print(f"未知模块: {args.module}")
            sys.exit(1)
    else:
        sys.exit(run_all_tests())
