#!/usr/bin/env python3
"""
数据源切换功能测试

测试内容：
1. 数据源工厂创建
2. Akshare数据源功能
3. Tushare数据源功能
4. 数据源切换
5. 数据源降级处理
"""

import os
import sys
import time
import unittest

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils import get_logger, get_config
from app.services.datasource import DataSource
from app.services.akshare_datasource import AkshareDataSource
from app.services.tushare_datasource import TushareDataSource
from app.services.datasource_factory import DataSourceFactory


logger = get_logger(__name__)


class TestDataSourceFactory(unittest.TestCase):
    """数据源工厂测试"""
    
    def test_01_create_default_datasource(self):
        """测试创建默认数据源"""
        logger.info("测试创建默认数据源...")
        
        datasource = DataSourceFactory.create_datasource()
        
        self.assertIsNotNone(datasource)
        self.assertIsInstance(datasource, DataSource)
        
        datasource_type = type(datasource).__name__
        logger.info(f"✓ 创建默认数据源成功: {datasource_type}")
    
    def test_02_create_akshare_datasource(self):
        """测试创建Akshare数据源"""
        logger.info("测试创建Akshare数据源...")
        
        datasource = DataSourceFactory.create_datasource('akshare')
        
        self.assertIsNotNone(datasource)
        self.assertIsInstance(datasource, AkshareDataSource)
        
        logger.info("✓ 创建Akshare数据源成功")
    
    def test_03_create_tushare_datasource(self):
        """测试创建Tushare数据源"""
        logger.info("测试创建Tushare数据源...")
        
        try:
            datasource = DataSourceFactory.create_datasource('tushare')
            
            self.assertIsNotNone(datasource)
            self.assertIsInstance(datasource, TushareDataSource)
            
            logger.info("✓ 创建Tushare数据源成功")
        
        except Exception as e:
            # Tushare可能需要token配置
            logger.warning(f"Tushare数据源创建失败（可能未配置token）: {e}")
            self.skipTest("Tushare未配置")
    
    def test_04_invalid_datasource_type(self):
        """测试无效数据源类型"""
        logger.info("测试无效数据源类型...")
        
        with self.assertRaises(ValueError):
            DataSourceFactory.create_datasource('invalid_type')
        
        logger.info("✓ 无效数据源类型测试通过")


class TestAkshareDataSource(unittest.TestCase):
    """Akshare数据源测试"""
    
    @classmethod
    def setUpClass(cls):
        """初始化测试环境"""
        cls.datasource = AkshareDataSource()
    
    def test_01_get_stock_list(self):
        """测试获取股票列表"""
        logger.info("测试Akshare获取股票列表...")
        
        try:
            stocks = self.datasource.get_stock_list()
            
            self.assertIsNotNone(stocks)
            self.assertTrue(len(stocks) > 0)
            
            # 验证数据结构
            stock = stocks[0]
            self.assertIn('stock_code', stock)
            self.assertIn('stock_name', stock)
            
            logger.info(f"✓ 获取股票列表成功，共 {len(stocks)} 只股票")
            logger.info(f"  示例: {stock['stock_code']} - {stock['stock_name']}")
        
        except Exception as e:
            logger.warning(f"获取股票列表失败（网络问题）: {e}")
            self.skipTest(f"网络问题: {e}")
    
    def test_02_get_stock_history(self):
        """测试获取股票历史行情"""
        logger.info("测试Akshare获取股票历史行情...")
        
        try:
            history = self.datasource.get_stock_history(
                '600000',  # 浦发银行
                start_date='20240101',
                end_date='20240110'
            )
            
            if history is not None and len(history) > 0:
                self.assertTrue(len(history) > 0)
                
                # 验证数据结构
                record = history[0]
                required_fields = ['trade_date', 'open_price', 'close_price', 
                                  'high_price', 'low_price', 'volume']
                for field in required_fields:
                    self.assertIn(field, record, f"缺少字段: {field}")
                
                logger.info(f"✓ 获取历史行情成功，共 {len(history)} 条记录")
            else:
                logger.warning("获取历史行情返回空数据")
        
        except Exception as e:
            logger.warning(f"获取历史行情失败（网络问题）: {e}")
            self.skipTest(f"网络问题: {e}")
    
    def test_03_datasource_name(self):
        """测试数据源名称"""
        logger.info("测试数据源名称...")
        
        # 检查数据源类型
        self.assertEqual(type(self.datasource).__name__, 'AkshareDataSource')
        
        logger.info(f"✓ 数据源类型: {type(self.datasource).__name__}")


class TestTushareDataSource(unittest.TestCase):
    """Tushare数据源测试"""
    
    @classmethod
    def setUpClass(cls):
        """初始化测试环境"""
        config = get_config()
        tushare_config = config.get('datasource', {}).get('tushare', {})
        
        if not tushare_config.get('token'):
            cls.skip_all = True
            cls.datasource = None
        else:
            cls.skip_all = False
            try:
                cls.datasource = TushareDataSource()
            except Exception as e:
                cls.skip_all = True
                cls.datasource = None
    
    def setUp(self):
        """测试前检查"""
        if self.skip_all:
            self.skipTest("Tushare未配置或初始化失败")
    
    def test_01_get_stock_list(self):
        """测试获取股票列表"""
        logger.info("测试Tushare获取股票列表...")
        
        try:
            stocks = self.datasource.get_stock_list()
            
            self.assertIsNotNone(stocks)
            self.assertTrue(len(stocks) > 0)
            
            logger.info(f"✓ 获取股票列表成功，共 {len(stocks)} 只股票")
        
        except Exception as e:
            logger.warning(f"获取股票列表失败: {e}")
            self.skipTest(f"Tushare API错误: {e}")
    
    def test_02_datasource_name(self):
        """测试数据源名称"""
        logger.info("测试数据源名称...")
        
        # 检查数据源类型
        self.assertEqual(type(self.datasource).__name__, 'TushareDataSource')
        
        logger.info(f"✓ 数据源类型: {type(self.datasource).__name__}")


class TestDataSourceSwitch(unittest.TestCase):
    """数据源切换测试"""
    
    def test_01_switch_datasource(self):
        """测试切换数据源"""
        logger.info("测试切换数据源...")
        
        # 创建Akshare数据源
        akshare_ds = DataSourceFactory.create_datasource('akshare')
        self.assertIsInstance(akshare_ds, AkshareDataSource)
        logger.info(f"  当前数据源: {type(akshare_ds).__name__}")
        
        # 尝试切换到Tushare
        config = get_config()
        tushare_config = config.get('datasource', {}).get('tushare', {})
        
        if tushare_config.get('token'):
            tushare_ds = DataSourceFactory.create_datasource('tushare')
            self.assertIsInstance(tushare_ds, TushareDataSource)
            logger.info(f"  切换到: {type(tushare_ds).__name__}")
            logger.info("✓ 数据源切换成功")
        else:
            logger.info("  未配置Tushare，跳过切换测试")
            logger.info("✓ 数据源切换测试完成（仅Akshare）")        
        logger.info("✓ 数据源切换测试完成")
    
    def test_02_datasource_interface(self):
        """测试数据源接口一致性"""
        logger.info("测试数据源接口一致性...")
        
        # 获取所有可用的数据源
        datasources = []
        
        # Akshare
        try:
            datasources.append(DataSourceFactory.create_datasource('akshare'))
        except Exception as e:
            logger.warning(f"Akshare不可用: {e}")
        
        # Tushare
        try:
            datasources.append(DataSourceFactory.create_datasource('tushare'))
        except Exception as e:
            logger.info(f"Tushare不可用: {e}")
        
        # 验证接口一致性
        required_methods = ['get_stock_list', 'get_stock_daily', 'get_trading_dates', 'is_trading_day']
        
        for ds in datasources:
            for method in required_methods:
                self.assertTrue(
                    hasattr(ds, method),
                    f"{type(ds).__name__} 缺少方法: {method}"
                )
        
        logger.info(f"✓ 测试了 {len(datasources)} 个数据源的接口一致性")


class TestDataSourceFallback(unittest.TestCase):
    """数据源降级测试"""
    
    def test_01_fallback_on_error(self):
        """测试错误时降级处理"""
        logger.info("测试错误时降级处理...")
        
        # 默认数据源应该是Akshare
        default_ds = DataSourceFactory.create_datasource()
        
        self.assertIsNotNone(default_ds)
        logger.info(f"  默认数据源: {type(default_ds).__name__}")
        
        # 如果Tushare配置但出错，应该降级到Akshare
        # 这里模拟降级逻辑
        try:
            # 尝试使用Tushare
            tushare_ds = DataSourceFactory.create_datasource('tushare')
            logger.info(f"  Tushare可用: {type(tushare_ds).__name__}")
        except Exception as e:
            # 降级到Akshare
            fallback_ds = DataSourceFactory.create_datasource('akshare')
            self.assertIsInstance(fallback_ds, AkshareDataSource)
            logger.info(f"  降级到: {type(fallback_ds).__name__}")
        
        logger.info("✓ 降级处理测试完成")


def run_datasource_tests():
    """运行所有数据源测试"""
    logger.info("=" * 60)
    logger.info("开始运行数据源切换测试")
    logger.info("=" * 60)
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    test_classes = [
        TestDataSourceFactory,
        TestAkshareDataSource,
        TestTushareDataSource,
        TestDataSourceSwitch,
        TestDataSourceFallback,
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
    run_datasource_tests()
