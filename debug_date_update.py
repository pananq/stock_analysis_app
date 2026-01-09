#!/usr/bin/env python3
"""
调试脚本：检查为什么 latest_data_date 没有被更新
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from app.utils import get_logger, setup_logging
from app.utils.config import get_config
from app.models.database_factory import DatabaseFactory
from app.services.stock_date_range_service import StockDateRangeService


def debug_date_update():
    """调试日期更新问题"""
    logger = get_logger(__name__)
    
    try:
        # 加载配置
        config = get_config()
        
        # 初始化数据库
        db_factory = DatabaseFactory()
        database = db_factory.get_database(config=config.get('database.mysql'))
        
        logger.info("=" * 80)
        logger.info("开始调试日期更新问题")
        logger.info("=" * 80)
        
        # 1. 检查 stocks 表中有 NULL 字段的股票
        query = """
            SELECT code, name, earliest_data_date, latest_data_date
            FROM stocks
            WHERE earliest_data_date IS NULL OR latest_data_date IS NULL
            LIMIT 5
        """
        null_stocks = database.execute_query(query)
        
        logger.info(f"找到 {len(null_stocks)} 只股票有 NULL 日期字段:")
        for stock in null_stocks:
            logger.info(f"  股票: {stock['code']} - {stock['name']}")
            logger.info(f"    earliest_data_date: {stock.get('earliest_data_date')}")
            logger.info(f"    latest_data_date: {stock.get('latest_data_date')}")
        
        if not null_stocks:
            logger.info("没有找到有 NULL 日期字段的股票")
            return
        
        # 2. 对于第一个股票，检查 daily_market 表中的数据
        test_stock = null_stocks[0]
        stock_code = test_stock['code']
        
        logger.info("\n" + "=" * 80)
        logger.info(f"检查股票 {stock_code} 在 daily_market 表中的数据")
        logger.info("=" * 80)
        
        query = f"""
            SELECT MIN(trade_date) as min_date, MAX(trade_date) as max_date, COUNT(*) as count
            FROM daily_market
            WHERE code = %s
        """
        result = database.execute_query(query, (stock_code,))
        
        if result:
            row = result[0]
            logger.info(f"  min_date: {row.get('min_date')}")
            logger.info(f"  max_date: {row.get('max_date')}")
            logger.info(f"  数据条数: {row.get('count')}")
            
            # 检查数据类型
            min_date = row.get('min_date')
            max_date = row.get('max_date')
            logger.info(f"  min_date 类型: {type(min_date)}")
            logger.info(f"  max_date 类型: {type(max_date)}")
            
            # 3. 测试单条更新
            logger.info("\n" + "=" * 80)
            logger.info("测试单条更新")
            logger.info("=" * 80)
            
            if min_date and max_date:
                # 转换为字符串
                if isinstance(min_date, str):
                    min_date_str = min_date
                else:
                    min_date_str = min_date.strftime('%Y-%m-%d')
                
                if isinstance(max_date, str):
                    max_date_str = max_date
                else:
                    max_date_str = max_date.strftime('%Y-%m-%d')
                
                logger.info(f"  准备更新:")
                logger.info(f"    earliest_data_date = {min_date_str}")
                logger.info(f"    latest_data_date = {max_date_str}")
                
                query = """
                    UPDATE stocks
                    SET earliest_data_date = %s,
                        latest_data_date = %s,
                        updated_at = %s
                    WHERE code = %s
                """
                params = (min_date_str, max_date_str, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), stock_code)
                
                affected_rows = database.execute_update(query, params)
                logger.info(f"  更新影响行数: {affected_rows}")
                
                # 4. 验证更新结果
                logger.info("\n" + "=" * 80)
                logger.info("验证更新结果")
                logger.info("=" * 80)
                
                query = """
                    SELECT code, name, earliest_data_date, latest_data_date
                    FROM stocks
                    WHERE code = %s
                """
                result = database.execute_query(query, (stock_code,))
                
                if result:
                    row = result[0]
                    logger.info(f"  股票: {row['code']} - {row['name']}")
                    logger.info(f"    earliest_data_date: {row.get('earliest_data_date')}")
                    logger.info(f"    latest_data_date: {row.get('latest_data_date')}")
                    
                    if row.get('earliest_data_date') and row.get('latest_data_date'):
                        logger.info("  ✓ 更新成功！")
                    else:
                        logger.error("  ✗ 更新失败，字段仍为 NULL")
            else:
                logger.warning("  daily_market 表中没有数据，无法测试更新")
        else:
            logger.warning(f"  daily_market 表中没有股票 {stock_code} 的数据")
        
        logger.info("\n" + "=" * 80)
        logger.info("调试完成")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"调试失败: {e}", exc_info=True)


if __name__ == "__main__":
    # 加载配置并初始化日志系统
    config = get_config()
    setup_logging(config)
    
    logger = get_logger(__name__)
    
    debug_date_update()
