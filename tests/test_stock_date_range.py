#!/usr/bin/env python3
"""
单元测试：股票日期字段维护逻辑
测试 StockDateRangeService 的各个方法以及与 MarketDataService 的集成
"""

import sys
import os
import unittest
from datetime import datetime, date, timedelta

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.stock_date_range_service import StockDateRangeService
from app.services.market_data_service import MarketDataService
from app.models.mysql_db import get_mysql_db
from app.utils.config import get_config


class TestStockDateRangeService(unittest.TestCase):
    """测试 StockDateRangeService"""
    
    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        cls.logger = None
        cls.db = None
        cls.service = None
        cls.test_stock_code = '600000'
        
        try:
            config = get_config()
            cls.db = get_mysql_db()
            cls.service = StockDateRangeService(cls.db)
            cls.logger = cls.service.logger
            
            # 清理测试数据
            cls._cleanup_test_data()
            
            # 准备测试数据：在 daily_market 表中插入测试数据
            cls._prepare_test_data()
            
        except Exception as e:
            print(f"测试准备失败: {e}")
            raise
    
    @classmethod
    def tearDownClass(cls):
        """测试后清理"""
        try:
            if cls.service:
                cls._cleanup_test_data()
        except Exception as e:
            print(f"测试清理失败: {e}")
    
    @classmethod
    def _cleanup_test_data(cls):
        """清理测试数据"""
        if not cls.db:
            return
        
        try:
            # 删除 daily_market 表中的测试数据
            query = "DELETE FROM daily_market WHERE code = %s"
            cls.db.execute_update(query, (cls.test_stock_code,))
            
            # 重置 stocks 表中的日期字段
            query = """
                UPDATE stocks 
                SET earliest_data_date = NULL, latest_data_date = NULL 
                WHERE code = %s
            """
            cls.db.execute_update(query, (cls.test_stock_code,))
            
        except Exception as e:
            print(f"清理测试数据失败: {e}")
    
    @classmethod
    def _prepare_test_data(cls):
        """准备测试数据"""
        if not cls.db:
            return
        
        try:
            # 在 daily_market 表中插入测试数据
            base_date = date.today() - timedelta(days=10)
            test_dates = [
                base_date + timedelta(days=i)
                for i in range(10)  # 插入10天的数据
            ]
            
            for test_date in test_dates:
                query = """
                    INSERT INTO daily_market 
                    (code, trade_date, open, close, high, low, volume, amount, created_at)
                    VALUES (%s, %s, 10.0, 10.5, 10.8, 9.8, 1000000, 10000000, %s)
                """
                cls.db.execute_update(query, (
                    cls.test_stock_code,
                    test_date.strftime('%Y-%m-%d'),
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ))
            
            cls.logger.info(f"准备测试数据: {test_dates[0]} ~ {test_dates[-1]}")
            
        except Exception as e:
            print(f"准备测试数据失败: {e}")
            raise
    
    def test_get_stock_date_range_from_daily_market(self):
        """测试从 daily_market 表获取日期范围"""
        earliest, latest = self.service.get_stock_date_range_from_daily_market(self.test_stock_code)
        
        self.assertIsNotNone(earliest, "earliest_date 不应为 None")
        self.assertIsNotNone(latest, "latest_date 不应为 None")
        self.assertIsInstance(earliest, date, "earliest_date 应为 date 类型")
        self.assertIsInstance(latest, date, "latest_date 应为 date 类型")
        self.assertLessEqual(earliest, latest, "earliest_date 应早于或等于 latest_date")
        
        self.logger.info(f"✓ test_get_stock_date_range_from_daily_market: {earliest} ~ {latest}")
    
    def test_update_stock_date_range(self):
        """测试更新股票日期范围"""
        # 先重置日期字段
        query = """
            UPDATE stocks 
            SET earliest_data_date = NULL, latest_data_date = NULL 
            WHERE code = %s
        """
        self.db.execute_update(query, (self.test_stock_code,))
        
        # 获取测试数据的日期范围
        expected_earliest, expected_latest = self.service.get_stock_date_range_from_daily_market(
            self.test_stock_code
        )
        
        # 更新日期范围
        success = self.service.update_stock_date_range(
            self.test_stock_code,
            earliest_date=expected_earliest,
            latest_date=expected_latest
        )
        
        self.assertTrue(success, "更新应成功")
        
        # 验证更新结果
        query = """
            SELECT earliest_data_date, latest_data_date 
            FROM stocks 
            WHERE code = %s
        """
        results = self.db.execute_query(query, (self.test_stock_code,))
        
        self.assertEqual(len(results), 1, "应找到一条记录")
        
        result = results[0]
        actual_earliest = result.get('earliest_data_date')
        actual_latest = result.get('latest_data_date')
        
        # 转换为 date 对象进行比较
        if actual_earliest and isinstance(actual_earliest, str):
            actual_earliest = datetime.strptime(actual_earliest, '%Y-%m-%d').date()
        if actual_latest and isinstance(actual_latest, str):
            actual_latest = datetime.strptime(actual_latest, '%Y-%m-%d').date()
        
        self.assertEqual(actual_earliest, expected_earliest, "earliest_date 应正确更新")
        self.assertEqual(actual_latest, expected_latest, "latest_date 应正确更新")
        
        self.logger.info(f"✓ test_update_stock_date_range: {actual_earliest} ~ {actual_latest}")
    
    def test_batch_get_stock_date_range_from_daily_market(self):
        """测试批量查询日期范围"""
        # 使用测试股票代码
        stock_codes = [self.test_stock_code]
        
        results = self.service.batch_get_stock_date_range_from_daily_market(stock_codes)
        
        self.assertIn(self.test_stock_code, results, f"结果应包含 {self.test_stock_code}")
        
        earliest, latest = results[self.test_stock_code]
        self.assertIsNotNone(earliest, "earliest_date 不应为 None")
        self.assertIsNotNone(latest, "latest_date 不应为 None")
        
        self.logger.info(f"✓ test_batch_get_stock_date_range_from_daily_market: {earliest} ~ {latest}")
    
    def test_batch_update_stock_date_ranges(self):
        """测试批量更新日期范围"""
        # 准备测试数据
        updates = {
            self.test_stock_code: (
                date.today() - timedelta(days=20),
                date.today()
            )
        }
        
        success_count = self.service.batch_update_stock_date_ranges(updates)
        
        self.assertEqual(success_count, 1, "应成功更新 1 只股票")
        
        # 验证更新结果
        query = """
            SELECT earliest_data_date, latest_data_date 
            FROM stocks 
            WHERE code = %s
        """
        results = self.db.execute_query(query, (self.test_stock_code,))
        
        self.assertEqual(len(results), 1, "应找到一条记录")
        
        self.logger.info(f"✓ test_batch_update_stock_date_ranges: 成功更新 {success_count} 只股票")
    
    def test_batch_update_stock_date_ranges_optimized(self):
        """测试优化版批量更新日期范围"""
        # 准备测试数据
        updates = {
            self.test_stock_code: (
                date.today() - timedelta(days=30),
                date.today()
            )
        }
        
        success_count = self.service.batch_update_stock_date_ranges_optimized(updates, batch_size=100)
        
        self.assertEqual(success_count, 1, "应成功更新 1 只股票")
        
        # 验证更新结果
        query = """
            SELECT earliest_data_date, latest_data_date 
            FROM stocks 
            WHERE code = %s
        """
        results = self.db.execute_query(query, (self.test_stock_code,))
        
        self.assertEqual(len(results), 1, "应找到一条记录")
        
        self.logger.info(f"✓ test_batch_update_stock_date_ranges_optimized: 成功更新 {success_count} 只股票")
    
    def test_get_stocks_with_null_date_range(self):
        """测试获取日期字段为 NULL 的股票"""
        # 先重置测试股票的日期字段
        query = """
            UPDATE stocks 
            SET earliest_data_date = NULL, latest_data_date = NULL 
            WHERE code = %s
        """
        self.db.execute_update(query, (self.test_stock_code,))
        
        null_stocks = self.service.get_stocks_with_null_date_range()
        
        # 检查结果是否包含测试股票
        test_stock_found = any(
            stock['code'] == self.test_stock_code 
            for stock in null_stocks
        )
        
        self.assertTrue(test_stock_found, f"结果应包含测试股票 {self.test_stock_code}")
        
        self.logger.info(f"✓ test_get_stocks_with_null_date_range: 找到 {len(null_stocks)} 只日期字段为 NULL 的股票")
    
    def test_update_date_range_from_data(self):
        """测试根据数据列表更新日期范围"""
        # 先重置日期字段
        query = """
            UPDATE stocks 
            SET earliest_data_date = NULL, latest_data_date = NULL 
            WHERE code = %s
        """
        self.db.execute_update(query, (self.test_stock_code,))
        
        # 准备测试数据列表
        data_list = [
            {
                'trade_date': (date.today() - timedelta(days=5)).strftime('%Y-%m-%d'),
                'close': 10.5
            },
            {
                'trade_date': date.today().strftime('%Y-%m-%d'),
                'close': 11.0
            }
        ]
        
        success, count = self.service.update_date_range_from_data(
            self.test_stock_code,
            data_list
        )
        
        self.assertTrue(success, "更新应成功")
        self.assertEqual(count, 2, "应处理 2 条数据")
        
        # 验证更新结果
        query = """
            SELECT earliest_data_date, latest_data_date 
            FROM stocks 
            WHERE code = %s
        """
        results = self.db.execute_query(query, (self.test_stock_code,))
        
        self.assertEqual(len(results), 1, "应找到一条记录")
        
        self.logger.info(f"✓ test_update_date_range_from_data: 成功更新，处理 {count} 条数据")


class TestMarketDataServiceIntegration(unittest.TestCase):
    """测试 MarketDataService 与日期字段的集成"""
    
    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        cls.logger = None
        cls.market_data_service = None
        cls.date_range_service = None
        cls.test_stock_code = '600519'
        
        try:
            cls.market_data_service = MarketDataService()
            cls.date_range_service = StockDateRangeService(get_mysql_db())
            cls.logger = cls.market_data_service.logger
            
        except Exception as e:
            print(f"测试准备失败: {e}")
            raise
    
    def test_save_daily_data_with_date_range_update(self):
        """测试 _save_daily_data 方法时更新日期字段"""
        # 准备测试数据
        import pandas as pd
        
        test_data = pd.DataFrame([
            {
                'trade_date': (date.today() - timedelta(days=2)).strftime('%Y-%m-%d'),
                'open': 100.0,
                'close': 101.0,
                'high': 102.0,
                'low': 99.0,
                'volume': 1000000,
                'amount': 10000000.0,
                'change_pct': 1.0,
                'turnover_rate': 1.0
            },
            {
                'trade_date': (date.today() - timedelta(days=1)).strftime('%Y-%m-%d'),
                'open': 101.0,
                'close': 102.0,
                'high': 103.0,
                'low': 100.0,
                'volume': 1000000,
                'amount': 10000000.0,
                'change_pct': 1.0,
                'turnover_rate': 1.0
            }
        ])
        
        # 保存数据并更新日期范围
        self.market_data_service._save_daily_data(
            test_data,
            self.test_stock_code,
            update_date_range=True
        )
        
        # 验证日期字段是否已更新
        earliest, latest = self.date_range_service.get_stock_date_range(self.test_stock_code)
        
        self.assertIsNotNone(earliest, "earliest_date 不应为 None")
        self.assertIsNotNone(latest, "latest_date 不应为 None")
        
        self.logger.info(f"✓ test_save_daily_data_with_date_range_update: {earliest} ~ {latest}")


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加所有测试
    suite.addTests(loader.loadTestsFromTestCase(TestStockDateRangeService))
    suite.addTests(loader.loadTestsFromTestCase(TestMarketDataServiceIntegration))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 返回测试结果
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
