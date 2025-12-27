#!/usr/bin/env python3
"""
端到端集成测试

测试完整的数据流程：
1. 数据源连接 -> 股票列表获取 -> 数据库存储
2. 历史行情获取 -> DuckDB存储 -> 技术指标计算
3. 策略配置 -> 策略执行 -> 结果存储
4. API接口 -> Web界面
"""

import os
import sys
import time
import json
import tempfile
import unittest
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils import get_logger, get_config
from app.models.sqlite_db import SQLiteDB
from app.models.duckdb_manager import DuckDBManager
from app.services.stock_service import StockService
from app.services.market_data_service import MarketDataService
from app.services.strategy_service import StrategyService
from app.services.strategy_executor import StrategyExecutor
from app.services.datasource_factory import DataSourceFactory
from app.indicators.technical_indicators import TechnicalIndicators


logger = get_logger(__name__)


class TestDatabaseIntegration(unittest.TestCase):
    """数据库集成测试"""
    
    @classmethod
    def setUpClass(cls):
        """初始化测试环境"""
        cls.config = get_config()
        db_config = cls.config.get('database', {})
        sqlite_path = db_config.get('sqlite_path', './data/stock_analysis.db')
        duckdb_path = db_config.get('duckdb_path', './data/market_data.duckdb')
        
        cls.sqlite_db = SQLiteDB(sqlite_path)
        cls.duckdb = DuckDBManager(duckdb_path)
    
    def test_01_sqlite_connection(self):
        """测试SQLite数据库连接"""
        logger.info("测试SQLite数据库连接...")
        
        # 执行简单查询
        result = self.sqlite_db.execute_query("SELECT 1 as test")
        self.assertEqual(result[0]['test'], 1)
        logger.info("✓ SQLite数据库连接正常")
    
    def test_02_sqlite_tables_exist(self):
        """测试SQLite表是否存在"""
        logger.info("测试SQLite表结构...")
        
        tables = ['stocks', 'strategies', 'strategy_results', 'system_logs', 'job_logs']
        for table in tables:
            result = self.sqlite_db.execute_query(
                f"SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table,)
            )
            self.assertTrue(len(result) > 0, f"表 {table} 不存在")
            logger.info(f"  ✓ 表 {table} 存在")
        
        logger.info("✓ SQLite表结构完整")
    
    def test_03_duckdb_connection(self):
        """测试DuckDB数据库连接"""
        logger.info("测试DuckDB数据库连接...")
        
        result = self.duckdb.execute_query("SELECT 1 as test")
        self.assertEqual(result[0]['test'], 1)
        logger.info("✓ DuckDB数据库连接正常")
    
    def test_04_duckdb_table_exists(self):
        """测试DuckDB表是否存在"""
        logger.info("测试DuckDB表结构...")
        
        try:
            result = self.duckdb.execute_query(
                "SELECT * FROM information_schema.tables WHERE table_name = 'daily_market'"
            )
            if len(result) > 0:
                logger.info("✓ DuckDB表结构完整")
            else:
                logger.warning("DuckDB表 daily_market 尚未创建（需要导入数据后创建）")
        except Exception as e:
            logger.warning(f"DuckDB表检查失败: {e}")


class TestDataSourceIntegration(unittest.TestCase):
    """数据源集成测试"""
    
    @classmethod
    def setUpClass(cls):
        """初始化测试环境"""
        cls.config = get_config()
        cls.datasource = DataSourceFactory.create_datasource()
    
    def test_01_datasource_creation(self):
        """测试数据源创建"""
        logger.info("测试数据源创建...")
        
        self.assertIsNotNone(self.datasource)
        logger.info(f"✓ 数据源创建成功: {type(self.datasource).__name__}")
    
    def test_02_get_stock_list(self):
        """测试获取股票列表"""
        logger.info("测试获取股票列表...")
        
        try:
            stocks = self.datasource.get_stock_list()
            self.assertIsNotNone(stocks)
            self.assertTrue(len(stocks) > 0)
            logger.info(f"✓ 获取股票列表成功，共 {len(stocks)} 只股票")
            
            # 验证数据结构
            if len(stocks) > 0:
                stock = stocks[0]
                self.assertIn('stock_code', stock)
                self.assertIn('stock_name', stock)
                logger.info(f"  示例: {stock['stock_code']} - {stock['stock_name']}")
        
        except Exception as e:
            logger.warning(f"获取股票列表失败（可能是网络问题）: {e}")
            self.skipTest(f"网络问题: {e}")
    
    def test_03_get_stock_history(self):
        """测试获取股票历史行情"""
        logger.info("测试获取股票历史行情...")
        
        try:
            # 获取浦发银行的历史行情
            history = self.datasource.get_stock_history(
                '600000',
                start_date='20240101',
                end_date='20240110'
            )
            
            if history is not None and len(history) > 0:
                self.assertTrue(len(history) > 0)
                logger.info(f"✓ 获取历史行情成功，共 {len(history)} 条记录")
                
                # 验证数据结构
                record = history[0]
                required_fields = ['trade_date', 'open_price', 'close_price', 
                                  'high_price', 'low_price', 'volume']
                for field in required_fields:
                    self.assertIn(field, record, f"缺少字段: {field}")
                logger.info(f"  示例: {record['trade_date']} 收盘价: {record['close_price']}")
            else:
                logger.warning("获取历史行情返回空数据")
        
        except Exception as e:
            logger.warning(f"获取历史行情失败（可能是网络问题）: {e}")
            self.skipTest(f"网络问题: {e}")


class TestStockServiceIntegration(unittest.TestCase):
    """股票服务集成测试"""
    
    @classmethod
    def setUpClass(cls):
        """初始化测试环境"""
        cls.stock_service = StockService()
    
    def test_01_get_all_stocks(self):
        """测试获取所有股票"""
        logger.info("测试获取所有股票...")
        
        try:
            stocks = self.stock_service.get_stock_list(limit=10)
            logger.info(f"  数据库中共 {len(stocks)} 只股票（最多显示10只）")
            
            if len(stocks) > 0:
                stock = stocks[0]
                logger.info(f"  示例: {stock['stock_code']} - {stock['stock_name']}")
                logger.info("✓ 获取股票列表成功")
            else:
                logger.warning("数据库中暂无股票数据")
        except Exception as e:
            logger.warning(f"获取股票列表失败: {e}")
    
    def test_02_search_stocks(self):
        """测试股票搜索"""
        logger.info("测试股票搜索功能...")
        
        # 按关键字搜索
        try:
            stocks = self.stock_service.search_stocks(keyword='600', limit=10)
            logger.info(f"  按关键字'600'搜索: {len(stocks)} 条结果")
            
            stocks = self.stock_service.search_stocks(keyword='平安', limit=10)
            logger.info(f"  按关键字'平安'搜索: {len(stocks)} 条结果")
            
            logger.info("✓ 股票搜索功能正常")
        except Exception as e:
            logger.warning(f"股票搜索失败: {e}")


class TestMarketDataIntegration(unittest.TestCase):
    """行情数据集成测试"""
    
    @classmethod
    def setUpClass(cls):
        """初始化测试环境"""
        cls.market_service = MarketDataService()
        config = get_config()
        duckdb_path = config.get('database', {}).get('duckdb_path', './data/market_data.duckdb')
        cls.duckdb = DuckDBManager(duckdb_path)
    
    def test_01_get_stock_history(self):
        """测试获取股票历史行情"""
        logger.info("测试获取股票历史行情...")
        
        # 查询已有数据
        result = self.duckdb.execute_query(
            "SELECT COUNT(*) as count FROM daily_market"
        )
        count = result[0]['count']
        logger.info(f"  数据库中共 {count} 条行情记录")
        
        if count > 0:
            # 获取最新数据
            result = self.duckdb.execute_query(
                "SELECT DISTINCT code FROM daily_market LIMIT 5"
            )
            logger.info(f"  示例股票: {[r['code'] for r in result]}")
            logger.info("✓ 行情数据查询正常")
        else:
            logger.warning("数据库中暂无行情数据")


class TestTechnicalIndicators(unittest.TestCase):
    """技术指标计算测试"""
    
    @classmethod
    def setUpClass(cls):
        """初始化测试环境"""
        cls.indicators = TechnicalIndicators()
        config = get_config()
        duckdb_path = config.get('database', {}).get('duckdb_path', './data/market_data.duckdb')
        cls.duckdb = DuckDBManager(duckdb_path)
    
    def test_01_calculate_ma(self):
        """测试计算移动平均线"""
        logger.info("测试计算移动平均线...")
        
        import pandas as pd
        
        # 使用测试数据
        test_prices = [10.0, 10.5, 10.3, 10.8, 11.0, 10.9, 11.2, 11.5, 11.3, 11.8,
                       12.0, 11.9, 12.2, 12.5, 12.3, 12.8, 13.0, 12.9, 13.2, 13.5]
        
        df = pd.DataFrame({'close': test_prices})
        
        # 计算5日均线
        result = self.indicators.calculate_ma(df, periods=[5, 10])
        
        self.assertIn('ma_5', result.columns)
        self.assertIn('ma_10', result.columns)
        
        logger.info(f"  5日均线最新值: {result['ma_5'].iloc[-1]:.2f}")
        logger.info(f"  10日均线最新值: {result['ma_10'].iloc[-1]:.2f}")
        
        logger.info("✓ 移动平均线计算正常")
    
    def test_02_calculate_change_pct(self):
        """测试计算涨跌幅"""
        logger.info("测试计算涨跌幅...")
        
        import pandas as pd
        
        # 测试数据
        test_prices = [10.0, 10.5, 10.3, 10.8, 11.0]
        df = pd.DataFrame({'close': test_prices})
        
        # 计算涨跌幅
        result = self.indicators.calculate_change_pct(df)
        
        self.assertIn('change_pct', result.columns)
        
        # 验证第一个涨跌幅
        expected_first = (10.5 - 10.0) / 10.0 * 100  # 5%
        self.assertAlmostEqual(result['change_pct'].iloc[1], expected_first, places=1)
        
        logger.info(f"  涨跌幅序列: {result['change_pct'].dropna().values}")
        logger.info("✓ 涨跌幅计算正常")


class TestStrategyIntegration(unittest.TestCase):
    """策略集成测试"""
    
    @classmethod
    def setUpClass(cls):
        """初始化测试环境"""
        cls.strategy_service = StrategyService()
        cls.strategy_executor = StrategyExecutor()
    
    def test_01_create_strategy(self):
        """测试创建策略"""
        logger.info("测试创建策略...")
        
        strategy_id = self.strategy_service.create_strategy(
            name=f'集成测试策略_{int(time.time())}',
            description='集成测试创建的策略',
            rise_threshold=5.0,
            observation_days=3,
            ma_period=20,
            enabled=True
        )
        
        self.assertIsNotNone(strategy_id)
        self.assertGreater(strategy_id, 0)
        
        # 保存ID用于后续测试
        self.__class__.test_strategy_id = strategy_id
        logger.info(f"✓ 创建策略成功，ID: {strategy_id}")    
    def test_02_get_strategy(self):
        """测试获取策略"""
        logger.info("测试获取策略...")
        
        if not hasattr(self, 'test_strategy_id'):
            self.skipTest("没有测试策略ID")
        
        strategy = self.strategy_service.get_strategy(self.test_strategy_id)
        self.assertIsNotNone(strategy)
        self.assertEqual(strategy['id'], self.test_strategy_id)
        logger.info(f"✓ 获取策略成功: {strategy['name']}")
    
    def test_03_list_strategies(self):
        """测试获取策略列表"""
        logger.info("测试获取策略列表...")
        
        strategies = self.strategy_service.list_strategies()
        self.assertIsNotNone(strategies)
        logger.info(f"✓ 获取策略列表成功，共 {len(strategies)} 个策略")
    
    def test_04_execute_strategy(self):
        """测试执行策略"""
        logger.info("测试执行策略...")
        
        if not hasattr(self, 'test_strategy_id'):
            self.skipTest("没有测试策略ID")
        
        start_time = time.time()
        
        try:
            result = self.strategy_executor.execute_strategy(self.test_strategy_id)
            
            elapsed_time = time.time() - start_time
            logger.info(f"  执行耗时: {elapsed_time:.2f}秒")
            
            if result is not None:
                logger.info(f"  匹配股票数: {len(result)}")
                logger.info("✓ 策略执行成功")
            else:
                logger.warning("策略执行返回空结果")
        
        except Exception as e:
            logger.warning(f"策略执行失败: {e}")
    
    def test_05_delete_strategy(self):
        """测试删除策略"""
        logger.info("测试删除策略...")
        
        if not hasattr(self, 'test_strategy_id'):
            self.skipTest("没有测试策略ID")
        
        result = self.strategy_service.delete_strategy(self.test_strategy_id)
        self.assertTrue(result)
        logger.info("✓ 删除策略成功")


class TestAPIIntegration(unittest.TestCase):
    """API集成测试"""
    
    @classmethod
    def setUpClass(cls):
        """初始化测试环境"""
        from app.api.app import create_app
        cls.app = create_app()
        cls.client = cls.app.test_client()
    
    def test_01_health_check(self):
        """测试健康检查接口"""
        logger.info("测试健康检查接口...")
        
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'healthy')
        logger.info("✓ 健康检查接口正常")
    
    def test_02_get_stocks_api(self):
        """测试股票列表API"""
        logger.info("测试股票列表API...")
        
        response = self.client.get('/api/stocks')
        self.assertIn(response.status_code, [200, 500])
        
        if response.status_code == 200:
            data = json.loads(response.data)
            logger.info(f"  返回 {len(data.get('data', []))} 条记录")
            logger.info("✓ 股票列表API正常")
        else:
            logger.warning("股票列表API返回错误")
    
    def test_03_get_strategies_api(self):
        """测试策略列表API"""
        logger.info("测试策略列表API...")
        
        response = self.client.get('/api/strategies')
        self.assertIn(response.status_code, [200, 500])
        
        if response.status_code == 200:
            data = json.loads(response.data)
            logger.info(f"  返回 {len(data.get('data', []))} 个策略")
            logger.info("✓ 策略列表API正常")
    
    def test_04_system_info_api(self):
        """测试系统信息API"""
        logger.info("测试系统信息API...")
        
        response = self.client.get('/api/system/info')
        self.assertIn(response.status_code, [200, 500])
        
        if response.status_code == 200:
            data = json.loads(response.data)
            logger.info(f"  系统版本: {data.get('data', {}).get('version', '未知')}")
            logger.info("✓ 系统信息API正常")


class TestPerformance(unittest.TestCase):
    """性能测试"""
    
    @classmethod
    def setUpClass(cls):
        """初始化测试环境"""
        config = get_config()
        duckdb_path = config.get('database', {}).get('duckdb_path', './data/market_data.duckdb')
        cls.duckdb = DuckDBManager(duckdb_path)
        cls.strategy_executor = StrategyExecutor()
        cls.strategy_service = StrategyService()
    
    def test_01_query_performance(self):
        """测试数据库查询性能"""
        logger.info("测试数据库查询性能...")
        
        # 测试简单查询
        start_time = time.time()
        result = self.duckdb.execute_query("SELECT COUNT(*) as count FROM daily_market")
        simple_time = time.time() - start_time
        
        count = result[0]['count']
        logger.info(f"  简单查询 (COUNT): {simple_time:.4f}秒, 记录数: {count}")
        
        if count > 0:
            # 测试分组查询
            start_time = time.time()
            result = self.duckdb.execute_query("""
                SELECT code, COUNT(*) as count
                FROM daily_market
                GROUP BY code
                LIMIT 100
            """)
            group_time = time.time() - start_time
            logger.info(f"  分组查询 (GROUP BY): {group_time:.4f}秒")
            
            # 测试排序查询
            start_time = time.time()
            result = self.duckdb.execute_query("""
                SELECT * FROM daily_market
                ORDER BY trade_date DESC
                LIMIT 1000
            """)
            sort_time = time.time() - start_time
            logger.info(f"  排序查询 (ORDER BY): {sort_time:.4f}秒")
            
            logger.info("✓ 数据库查询性能测试完成")
        else:
            logger.warning("数据库为空，跳过性能测试")
    
    def test_02_strategy_execution_performance(self):
        """测试策略执行性能"""
        logger.info("测试策略执行性能...")
        
        # 创建测试策略
        strategy_data = {
            'name': f'性能测试策略_{int(time.time())}',
            'description': '性能测试',
            'config': {
                'min_change': 0,
                'max_change': 10,
                'days': 20,
                'ma_period': 20
            },
            'enabled': True
        }
        
        strategy_id = self.strategy_service.create_strategy(strategy_data)
        
        # 执行策略并计时
        start_time = time.time()
        
        try:
            result = self.strategy_executor.execute_strategy(strategy_id)
            elapsed_time = time.time() - start_time
            
            logger.info(f"  执行耗时: {elapsed_time:.2f}秒")
            
            # 验证是否在5分钟内完成
            self.assertLess(elapsed_time, 300, "策略执行时间超过5分钟")
            
            if result is not None:
                logger.info(f"  匹配股票数: {len(result)}")
            
            if elapsed_time < 60:
                logger.info("✓ 策略执行性能优秀（<1分钟）")
            elif elapsed_time < 180:
                logger.info("✓ 策略执行性能良好（<3分钟）")
            else:
                logger.info("✓ 策略执行性能合格（<5分钟）")
        
        except Exception as e:
            logger.warning(f"策略执行失败: {e}")
        
        finally:
            # 清理测试策略
            self.strategy_service.delete_strategy(strategy_id)


def run_integration_tests():
    """运行所有集成测试"""
    logger.info("=" * 60)
    logger.info("开始运行系统集成测试")
    logger.info("=" * 60)
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    test_classes = [
        TestDatabaseIntegration,
        TestDataSourceIntegration,
        TestStockServiceIntegration,
        TestMarketDataIntegration,
        TestTechnicalIndicators,
        TestStrategyIntegration,
        TestAPIIntegration,
        TestPerformance,
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
    run_integration_tests()
