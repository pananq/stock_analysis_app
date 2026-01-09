#!/usr/bin/env python3
"""
集成测试：股票日期字段维护完整流程
测试从初始化修复到增量更新的完整流程
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
from app.utils.config import load_config


class TestStockDateRangeIntegration(unittest.TestCase):
    """集成测试：股票日期字段维护完整流程"""
    
    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        cls.logger = None
        cls.db = None
        cls.date_range_service = None
        cls.market_data_service = None
        cls.test_stock_codes = ['600000', '600519']
        
        try:
            config = load_config()
            cls.db = get_mysql_db()
            cls.date_range_service = StockDateRangeService(cls.db)
            cls.market_data_service = MarketDataService()
            cls.logger = cls.date_range_service.logger
            
            # 清理测试数据
            cls._cleanup_test_data()
            
        except Exception as e:
            print(f"测试准备失败: {e}")
            raise
    
    @classmethod
    def tearDownClass(cls):
        """测试后清理"""
        try:
            if cls.db:
                cls._cleanup_test_data()
        except Exception as e:
            print(f"测试清理失败: {e}")
    
    @classmethod
    def _cleanup_test_data(cls):
        """清理测试数据"""
        for stock_code in cls.test_stock_codes:
            try:
                # 删除 daily_market 表中的测试数据
                query = "DELETE FROM daily_market WHERE code = %s"
                cls.db.execute_update(query, (stock_code,))
                
                # 重置 stocks 表中的日期字段
                query = """
                    UPDATE stocks 
                    SET earliest_data_date = NULL, latest_data_date = NULL 
                    WHERE code = %s
                """
                cls.db.execute_update(query, (stock_code,))
                
            except Exception as e:
                print(f"清理股票 {stock_code} 的测试数据失败: {e}")
    
    def test_complete_workflow(self):
        """测试完整工作流：初始化修复 -> 增量更新 -> 验证"""
        self.logger.info("=" * 80)
        self.logger.info("测试完整工作流")
        self.logger.info("=" * 80)
        
        # 步骤 1: 准备测试数据 - 在 daily_market 表中插入历史数据
        self.logger.info("\n步骤 1: 准备测试数据")
        self._prepare_daily_market_data()
        
        # 步骤 2: 验证 stocks 表中的日期字段为 NULL
        self.logger.info("\n步骤 2: 验证 stocks 表中的日期字段为 NULL")
        self._verify_null_date_fields()
        
        # 步骤 3: 执行初始化修复
        self.logger.info("\n步骤 3: 执行初始化修复")
        self._execute_initial_fix()
        
        # 步骤 4: 验证初始化修复结果
        self.logger.info("\n步骤 4: 验证初始化修复结果")
        self._verify_fix_result()
        
        # 步骤 5: 模拟增量更新 - 插入新数据
        self.logger.info("\n步骤 5: 模拟增量更新")
        self._simulate_incremental_update()
        
        # 步骤 6: 验证增量更新后的日期字段
        self.logger.info("\n步骤 6: 验证增量更新后的日期字段")
        self._verify_incremental_update_result()
        
        # 步骤 7: 测试批量更新性能
        self.logger.info("\n步骤 7: 测试批量更新性能")
        self._test_batch_update_performance()
        
        self.logger.info("\n" + "=" * 80)
        self.logger.info("完整工作流测试通过")
        self.logger.info("=" * 80)
    
    def _prepare_daily_market_data(self):
        """在 daily_market 表中准备测试数据"""
        base_date = date.today() - timedelta(days=20)
        
        for stock_code in self.test_stock_codes:
            # 为每只股票插入 20 天的历史数据
            for i in range(20):
                test_date = base_date + timedelta(days=i)
                
                query = """
                    INSERT INTO daily_market 
                    (code, trade_date, open, close, high, low, volume, amount, created_at)
                    VALUES (%s, %s, 10.0, 10.5, 10.8, 9.8, 1000000, 10000000, %s)
                """
                self.db.execute_update(query, (
                    stock_code,
                    test_date.strftime('%Y-%m-%d'),
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ))
            
            self.logger.info(f"为股票 {stock_code} 准备了 20 天的历史数据")
    
    def _verify_null_date_fields(self):
        """验证 stocks 表中的日期字段为 NULL"""
        for stock_code in self.test_stock_codes:
            query = """
                SELECT earliest_data_date, latest_data_date 
                FROM stocks 
                WHERE code = %s
            """
            results = self.db.execute_query(query, (stock_code,))
            
            self.assertEqual(len(results), 1, f"应找到股票 {stock_code}")
            
            result = results[0]
            earliest = result.get('earliest_data_date')
            latest = result.get('latest_data_date')
            
            self.assertIsNone(earliest, f"股票 {stock_code} 的 earliest_data_date 应为 NULL")
            self.assertIsNone(latest, f"股票 {stock_code} 的 latest_data_date 应为 NULL")
            
            self.logger.info(f"✓ 股票 {stock_code} 的日期字段为 NULL")
    
    def _execute_initial_fix(self):
        """执行初始化修复"""
        # 获取日期字段为 NULL 的股票
        null_stocks = self.date_range_service.get_stocks_with_null_date_range()
        
        self.assertGreater(len(null_stocks), 0, "应有需要修复的股票")
        
        # 批量查询日期范围
        stock_codes = [stock['code'] for stock in null_stocks if stock['code'] in self.test_stock_codes]
        date_ranges = self.date_range_service.batch_get_stock_date_range_from_daily_market(stock_codes)
        
        # 准备批量更新的数据
        updates = {}
        for stock in null_stocks:
            stock_code = stock['code']
            if stock_code not in self.test_stock_codes:
                continue
            
            earliest, latest = date_ranges.get(stock_code, (None, None))
            
            if earliest and latest:
                updates[stock_code] = (earliest, latest)
        
        # 批量更新
        success_count = self.date_range_service.batch_update_stock_date_ranges_optimized(updates)
        
        self.assertEqual(success_count, len(self.test_stock_codes), "应成功更新所有测试股票")
        
        self.logger.info(f"✓ 初始化修复完成，成功更新 {success_count} 只股票")
    
    def _verify_fix_result(self):
        """验证初始化修复结果"""
        for stock_code in self.test_stock_codes:
            earliest, latest = self.date_range_service.get_stock_date_range(stock_code)
            
            self.assertIsNotNone(earliest, f"股票 {stock_code} 的 earliest_data_date 不应为 NULL")
            self.assertIsNotNone(latest, f"股票 {stock_code} 的 latest_data_date 不应为 NULL")
            
            # 验证日期范围是否正确
            expected_earliest, expected_latest = self.date_range_service.get_stock_date_range_from_daily_market(
                stock_code
            )
            
            self.assertEqual(earliest, expected_earliest, "earliest_date 应与 daily_market 表一致")
            self.assertEqual(latest, expected_latest, "latest_date 应与 daily_market 表一致")
            
            self.logger.info(f"✓ 股票 {stock_code} 日期范围正确: {earliest} ~ {latest}")
    
    def _simulate_incremental_update(self):
        """模拟增量更新"""
        import pandas as pd
        
        # 为每只股票插入新的数据（比最新日期晚 1 天）
        for stock_code in self.test_stock_codes:
            # 获取当前最新日期
            _, current_latest = self.date_range_service.get_stock_date_range(stock_code)
            
            # 插入新数据
            new_date = current_latest + timedelta(days=1)
            
            test_data = pd.DataFrame([{
                'trade_date': new_date.strftime('%Y-%m-%d'),
                'open': 11.0,
                'close': 11.5,
                'high': 12.0,
                'low': 10.5,
                'volume': 1000000,
                'amount': 10000000.0,
                'change_pct': 1.0,
                'turnover_rate': 1.0
            }])
            
            # 保存数据并更新日期范围
            self.market_data_service._save_daily_data(
                test_data,
                stock_code,
                update_date_range=True
            )
            
            self.logger.info(f"✓ 股票 {stock_code} 插入新数据: {new_date}")
    
    def _verify_incremental_update_result(self):
        """验证增量更新后的日期字段"""
        for stock_code in self.test_stock_codes:
            earliest, latest = self.date_range_service.get_stock_date_range(stock_code)
            
            self.assertIsNotNone(earliest, f"股票 {stock_code} 的 earliest_data_date 不应为 NULL")
            self.assertIsNotNone(latest, f"股票 {stock_code} 的 latest_data_date 不应为 NULL")
            
            # 验证 latest_date 是否已更新
            _, expected_latest = self.date_range_service.get_stock_date_range_from_daily_market(stock_code)
            
            self.assertEqual(latest, expected_latest, "latest_date 应已更新")
            
            self.logger.info(f"✓ 股票 {stock_code} 增量更新后日期范围正确: {earliest} ~ {latest}")
    
    def _test_batch_update_performance(self):
        """测试批量更新性能"""
        # 准备批量更新数据
        updates = {}
        for stock_code in self.test_stock_codes:
            updates[stock_code] = (
                date.today() - timedelta(days=100),
                date.today()
            )
        
        # 测试普通批量更新
        start_time = datetime.now()
        success_count_1 = self.date_range_service.batch_update_stock_date_ranges(updates)
        duration_1 = (datetime.now() - start_time).total_seconds()
        
        # 测试优化版批量更新
        start_time = datetime.now()
        success_count_2 = self.date_range_service.batch_update_stock_date_ranges_optimized(
            updates,
            batch_size=100
        )
        duration_2 = (datetime.now() - start_time).total_seconds()
        
        self.assertEqual(success_count_1, len(self.test_stock_codes), "普通批量更新应成功")
        self.assertEqual(success_count_2, len(self.test_stock_codes), "优化版批量更新应成功")
        
        self.logger.info(f"✓ 普通批量更新耗时: {duration_1:.3f} 秒")
        self.logger.info(f"✓ 优化版批量更新耗时: {duration_2:.3f} 秒")
        self.logger.info(f"✓ 性能提升: {(duration_1 - duration_2) / duration_1 * 100:.1f}%")


def run_tests():
    """运行所有集成测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加集成测试
    suite.addTests(loader.loadTestsFromTestCase(TestStockDateRangeIntegration))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 返回测试结果
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
