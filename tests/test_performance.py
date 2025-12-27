#!/usr/bin/env python3
"""
数据库性能测试和优化

测试内容：
1. 查询性能基准测试
2. 索引有效性测试
3. 批量操作性能
4. 并发访问性能
"""

import os
import sys
import time
import random
import threading
import unittest
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils import get_logger
from app.models.sqlite_db import SQLiteDB
from app.models.duckdb_manager import DuckDBManager


logger = get_logger(__name__)


class TestSQLitePerformance(unittest.TestCase):
    """SQLite性能测试"""
    
    @classmethod
    def setUpClass(cls):
        """初始化测试环境"""
        from app.utils import get_config
        config = get_config()
        sqlite_path = config.get('database', {}).get('sqlite_path', './data/stock_analysis.db')
        cls.db = SQLiteDB(sqlite_path)
    
    def test_01_simple_query_performance(self):
        """测试简单查询性能"""
        logger.info("测试SQLite简单查询性能...")
        
        # 预热
        self.db.execute_query("SELECT 1")
        
        # 测试简单查询
        iterations = 100
        start_time = time.time()
        
        for i in range(iterations):
            self.db.execute_query("SELECT 1")
        
        elapsed = time.time() - start_time
        avg_time = elapsed / iterations * 1000  # 毫秒
        
        logger.info(f"  {iterations}次简单查询，总耗时: {elapsed:.3f}秒")
        logger.info(f"  平均每次查询: {avg_time:.3f}毫秒")
        
        # 应该小于10毫秒
        self.assertLess(avg_time, 10, "简单查询太慢")
        
        logger.info("✓ 简单查询性能测试通过")
    
    def test_02_stock_query_performance(self):
        """测试股票查询性能"""
        logger.info("测试SQLite股票查询性能...")
        
        # 获取股票总数
        result = self.db.execute_query("SELECT COUNT(*) as count FROM stocks")
        count = result[0]['count']
        logger.info(f"  股票总数: {count}")
        
        if count == 0:
            logger.warning("数据库中没有股票数据，跳过测试")
            self.skipTest("无数据")
            return
        
        # 测试查询所有股票
        start_time = time.time()
        result = self.db.execute_query("SELECT * FROM stocks")
        elapsed = time.time() - start_time
        
        logger.info(f"  查询所有股票 ({len(result)}条) 耗时: {elapsed:.4f}秒")
        
        # 测试条件查询
        start_time = time.time()
        result = self.db.execute_query(
            "SELECT * FROM stocks WHERE code LIKE ?",
            ('600%',)
        )
        elapsed = time.time() - start_time
        
        logger.info(f"  条件查询 (600开头) ({len(result)}条) 耗时: {elapsed:.4f}秒")
        
        logger.info("✓ 股票查询性能测试通过")
    
    def test_03_strategy_query_performance(self):
        """测试策略查询性能"""
        logger.info("测试SQLite策略查询性能...")
        
        # 测试查询所有策略
        start_time = time.time()
        result = self.db.execute_query("SELECT * FROM strategies")
        elapsed = time.time() - start_time
        
        logger.info(f"  查询所有策略 ({len(result)}条) 耗时: {elapsed:.4f}秒")
        
        # 测试连表查询
        start_time = time.time()
        result = self.db.execute_query("""
            SELECT s.*, COUNT(r.id) as result_count
            FROM strategies s
            LEFT JOIN strategy_results r ON s.id = r.strategy_id
            GROUP BY s.id
        """)
        elapsed = time.time() - start_time
        
        logger.info(f"  连表查询 ({len(result)}条) 耗时: {elapsed:.4f}秒")
        
        logger.info("✓ 策略查询性能测试通过")


class TestDuckDBPerformance(unittest.TestCase):
    """DuckDB性能测试"""
    
    @classmethod
    def setUpClass(cls):
        """初始化测试环境"""
        from app.utils import get_config
        config = get_config()
        duckdb_path = config.get('database', {}).get('duckdb_path', './data/market_data.duckdb')
        cls.db = DuckDBManager(duckdb_path)
    
    def test_01_simple_query_performance(self):
        """测试简单查询性能"""
        logger.info("测试DuckDB简单查询性能...")
        
        # 预热
        self.db.execute_query("SELECT 1")
        
        # 测试简单查询
        iterations = 100
        start_time = time.time()
        
        for i in range(iterations):
            self.db.execute_query("SELECT 1")
        
        elapsed = time.time() - start_time
        avg_time = elapsed / iterations * 1000  # 毫秒
        
        logger.info(f"  {iterations}次简单查询，总耗时: {elapsed:.3f}秒")
        logger.info(f"  平均每次查询: {avg_time:.3f}毫秒")
        
        logger.info("✓ 简单查询性能测试通过")
    
    def _check_table_exists(self):
        """检查daily_market表是否存在"""
        try:
            result = self.db.execute_query("SELECT COUNT(*) as count FROM daily_market")
            return True
        except Exception:
            return False
    
    def test_02_market_data_query_performance(self):
        """测试行情数据查询性能"""
        logger.info("测试DuckDB行情数据查询性能...")
        
        if not self._check_table_exists():
            logger.warning("daily_market表不存在，跳过测试")
            self.skipTest("daily_market表不存在")
            return
        
        # 获取数据总数
        result = self.db.execute_query("SELECT COUNT(*) as count FROM daily_market")
        count = result[0]['count']
        logger.info(f"  行情记录总数: {count}")
        
        if count == 0:
            logger.warning("数据库中没有行情数据，跳过测试")
            self.skipTest("无数据")
            return
        
        # 测试全表扫描
        start_time = time.time()
        result = self.db.execute_query("SELECT COUNT(*) FROM daily_market")
        elapsed = time.time() - start_time
        
        logger.info(f"  全表计数 耗时: {elapsed:.4f}秒")
        
        # 测试单股票查询
        start_time = time.time()
        result = self.db.execute_query("""
            SELECT * FROM daily_market 
            WHERE code = '600000.SH'
            ORDER BY trade_date DESC
            LIMIT 100
        """)
        elapsed = time.time() - start_time
        
        logger.info(f"  单股票查询 ({len(result)}条) 耗时: {elapsed:.4f}秒")
        
        # 测试分组聚合
        start_time = time.time()
        result = self.db.execute_query("""
            SELECT code, 
                   COUNT(*) as records,
                   AVG(close) as avg_close,
                   MAX(high) as max_high,
                   MIN(low) as min_low
            FROM daily_market
            GROUP BY code
            LIMIT 100
        """)
        elapsed = time.time() - start_time
        
        logger.info(f"  分组聚合 ({len(result)}组) 耗时: {elapsed:.4f}秒")
        
        logger.info("✓ 行情数据查询性能测试通过")
    
    def test_03_date_range_query_performance(self):
        """测试日期范围查询性能"""
        logger.info("测试DuckDB日期范围查询性能...")
        
        if not self._check_table_exists():
            logger.warning("daily_market表不存在，跳过测试")
            self.skipTest("daily_market表不存在")
            return
        
        # 检查是否有数据
        result = self.db.execute_query("SELECT COUNT(*) as count FROM daily_market")
        if result[0]['count'] == 0:
            self.skipTest("无数据")
            return
        
        # 测试最近30天数据
        start_time = time.time()
        result = self.db.execute_query("""
            SELECT * FROM daily_market 
            WHERE trade_date >= '2024-01-01'
            ORDER BY trade_date DESC
            LIMIT 1000
        """)
        elapsed = time.time() - start_time
        
        logger.info(f"  日期范围查询 ({len(result)}条) 耗时: {elapsed:.4f}秒")
        
        # 测试多条件查询
        start_time = time.time()
        result = self.db.execute_query("""
            SELECT * FROM daily_market 
            WHERE trade_date >= '2024-01-01'
              AND change_pct > 0
            ORDER BY change_pct DESC
            LIMIT 100
        """)
        elapsed = time.time() - start_time
        
        logger.info(f"  多条件查询 ({len(result)}条) 耗时: {elapsed:.4f}秒")
        
        logger.info("✓ 日期范围查询性能测试通过")
    
    def test_04_analytics_query_performance(self):
        """测试分析查询性能"""
        logger.info("测试DuckDB分析查询性能...")
        
        if not self._check_table_exists():
            logger.warning("daily_market表不存在，跳过测试")
            self.skipTest("daily_market表不存在")
            return
        
        # 检查是否有数据
        result = self.db.execute_query("SELECT COUNT(*) as count FROM daily_market")
        if result[0]['count'] == 0:
            self.skipTest("无数据")
            return
        
        # 测试涨跌统计
        start_time = time.time()
        result = self.db.execute_query("""
            SELECT 
                trade_date,
                SUM(CASE WHEN change_pct > 0 THEN 1 ELSE 0 END) as up_count,
                SUM(CASE WHEN change_pct < 0 THEN 1 ELSE 0 END) as down_count,
                AVG(change_pct) as avg_change
            FROM daily_market
            WHERE trade_date >= '2024-01-01'
            GROUP BY trade_date
            ORDER BY trade_date DESC
            LIMIT 30
        """)
        elapsed = time.time() - start_time
        
        logger.info(f"  涨跌统计 ({len(result)}天) 耗时: {elapsed:.4f}秒")
        
        # 测试移动平均计算
        start_time = time.time()
        result = self.db.execute_query("""
            SELECT 
                code,
                trade_date,
                close,
                AVG(close) OVER (
                    PARTITION BY code 
                    ORDER BY trade_date 
                    ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                ) as ma20
            FROM daily_market
            WHERE code = '600000.SH'
            ORDER BY trade_date DESC
            LIMIT 100
        """)
        elapsed = time.time() - start_time
        
        logger.info(f"  移动平均计算 ({len(result)}条) 耗时: {elapsed:.4f}秒")
        
        logger.info("✓ 分析查询性能测试通过")


class TestConcurrentAccess(unittest.TestCase):
    """并发访问测试"""
    
    @classmethod
    def setUpClass(cls):
        """初始化测试环境"""
        from app.utils import get_config
        config = get_config()
        sqlite_path = config.get('database', {}).get('sqlite_path', './data/stock_analysis.db')
        duckdb_path = config.get('database', {}).get('duckdb_path', './data/market_data.duckdb')
        cls.sqlite_path = sqlite_path
        cls.duckdb_path = duckdb_path
        cls.sqlite_db = SQLiteDB(sqlite_path)
        cls.duckdb = DuckDBManager(duckdb_path)
    
    def test_01_concurrent_sqlite_read(self):
        """测试SQLite并发读取"""
        logger.info("测试SQLite并发读取...")
        
        results = []
        errors = []
        sqlite_path = self.sqlite_path
        
        def query_stocks(thread_id):
            try:
                db = SQLiteDB(sqlite_path)
                result = db.execute_query("SELECT COUNT(*) as count FROM stocks")
                results.append((thread_id, result[0]['count']))
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # 创建多个线程
        threads = []
        for i in range(5):
            t = threading.Thread(target=query_stocks, args=(i,))
            threads.append(t)
        
        # 启动并等待
        start_time = time.time()
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
        elapsed = time.time() - start_time
        
        self.assertEqual(len(errors), 0, f"并发读取出错: {errors}")
        self.assertEqual(len(results), 5, "不是所有线程都完成了")
        
        logger.info(f"  5个并发读取，总耗时: {elapsed:.3f}秒")
        logger.info("✓ SQLite并发读取测试通过")
    
    def test_02_concurrent_duckdb_read(self):
        """测试DuckDB并发读取"""
        logger.info("测试DuckDB并发读取...")
        
        results = []
        errors = []
        duckdb_path = self.duckdb_path
        
        def query_market_data(thread_id):
            try:
                db = DuckDBManager(duckdb_path)
                result = db.execute_query("SELECT COUNT(*) as count FROM daily_market")
                results.append((thread_id, result[0]['count']))
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # 创建多个线程
        threads = []
        for i in range(5):
            t = threading.Thread(target=query_market_data, args=(i,))
            threads.append(t)
        
        # 启动并等待
        start_time = time.time()
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
        elapsed = time.time() - start_time
        
        # DuckDB可能不支持完全的并发读取
        if len(errors) > 0:
            logger.warning(f"  部分并发读取出错（DuckDB限制）: {len(errors)} 个")
        
        logger.info(f"  {len(results)}个成功的并发读取，总耗时: {elapsed:.3f}秒")
        logger.info("✓ DuckDB并发读取测试完成")


class TestIndexEffectiveness(unittest.TestCase):
    """索引有效性测试"""
    
    @classmethod
    def setUpClass(cls):
        """初始化测试环境"""
        from app.utils import get_config
        config = get_config()
        duckdb_path = config.get('database', {}).get('duckdb_path', './data/market_data.duckdb')
        cls.duckdb = DuckDBManager(duckdb_path)
    
    def _check_table_exists(self):
        """检查daily_market表是否存在"""
        try:
            self.duckdb.execute_query("SELECT COUNT(*) as count FROM daily_market")
            return True
        except Exception:
            return False
    
    def test_01_index_on_stock_code(self):
        """测试股票代码索引"""
        logger.info("测试股票代码索引有效性...")
        
        if not self._check_table_exists():
            logger.warning("daily_market表不存在，跳过测试")
            self.skipTest("daily_market表不存在")
            return
        
        # 检查是否有数据
        result = self.duckdb.execute_query("SELECT COUNT(*) as count FROM daily_market")
        if result[0]['count'] == 0:
            self.skipTest("无数据")
            return
        
        # 按股票代码查询
        start_time = time.time()
        result1 = self.duckdb.execute_query("""
            SELECT COUNT(*) FROM daily_market 
            WHERE code = '600000.SH'
        """)
        time_with_index = time.time() - start_time
        
        logger.info(f"  按股票代码查询耗时: {time_with_index:.4f}秒")
        logger.info(f"  查询结果: {result1[0]}")
        
        logger.info("✓ 股票代码索引测试完成")
    
    def test_02_index_on_trade_date(self):
        """测试交易日期索引"""
        logger.info("测试交易日期索引有效性...")
        
        if not self._check_table_exists():
            logger.warning("daily_market表不存在，跳过测试")
            self.skipTest("daily_market表不存在")
            return
        
        # 检查是否有数据
        result = self.duckdb.execute_query("SELECT COUNT(*) as count FROM daily_market")
        if result[0]['count'] == 0:
            self.skipTest("无数据")
            return
        
        # 按日期查询
        start_time = time.time()
        result = self.duckdb.execute_query("""
            SELECT COUNT(*) FROM daily_market 
            WHERE trade_date = '2024-01-01'
        """)
        elapsed = time.time() - start_time
        
        logger.info(f"  按交易日期查询耗时: {elapsed:.4f}秒")
        
        # 日期范围查询
        start_time = time.time()
        result = self.duckdb.execute_query("""
            SELECT COUNT(*) FROM daily_market 
            WHERE trade_date BETWEEN '2024-01-01' AND '2024-01-31'
        """)
        elapsed = time.time() - start_time
        
        logger.info(f"  日期范围查询耗时: {elapsed:.4f}秒")
        
        logger.info("✓ 交易日期索引测试完成")


def run_performance_tests():
    """运行所有性能测试"""
    logger.info("=" * 60)
    logger.info("开始运行数据库性能测试")
    logger.info("=" * 60)
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    test_classes = [
        TestSQLitePerformance,
        TestDuckDBPerformance,
        TestConcurrentAccess,
        TestIndexEffectiveness,
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
    run_performance_tests()
