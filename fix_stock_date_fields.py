#!/usr/bin/env python3
"""
初始化修复已有数据的日期字段
扫描 stocks 表中日期字段为 NULL 的股票，从 daily_market 表中查询其历史数据日期范围，并更新到 stocks 表
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from app.utils import get_logger
from app.utils.config import get_config
from app.models.database_factory import DatabaseFactory
from app.services.stock_date_range_service import StockDateRangeService


def fix_null_stock_date_ranges():
    """
    修复已有数据的日期字段
    """
    logger = get_logger(__name__)
    
    try:
        # 加载配置
        config = get_config()
        
        # 初始化数据库
        db_factory = DatabaseFactory()
        database = db_factory.get_database(config=config.get('database.mysql'))
        
        # 创建日期范围服务
        date_range_service = StockDateRangeService(database)
        logger = date_range_service.logger
        logger.info("开始初始化修复股票日期字段")
        logger.info("=" * 80)
        
        # 获取日期字段为 NULL 的股票列表
        null_stocks = date_range_service.get_stocks_with_null_date_range()
        
        if not null_stocks:
            logger.info("没有需要修复的股票")
            return True
        
        total_count = len(null_stocks)
        logger.info(f"找到 {total_count} 只股票需要修复日期字段")
        
        # 批量查询日期范围
        stock_codes = [stock['code'] for stock in null_stocks]
        date_ranges = date_range_service.batch_get_stock_date_range_from_daily_market(stock_codes)
        
        # 准备批量更新的数据
        updates = {}
        for stock in null_stocks:
            stock_code = stock['code']
            stock_name = stock['name']
            
            earliest, latest = date_ranges.get(stock_code, (None, None))
            
            if earliest and latest:
                updates[stock_code] = (earliest, latest)
                logger.info(f"股票 {stock_code} - {stock_name}: {earliest} ~ {latest}")
            else:
                logger.warning(f"股票 {stock_code} - {stock_name}: daily_market 表中没有数据，跳过")
        
        if not updates:
            logger.warning("没有找到需要更新的股票")
            return True
        
        # 批量更新
        success_count = date_range_service.batch_update_stock_date_ranges_optimized(updates)
        
        logger.info("=" * 80)
        logger.info(f"初始化修复完成")
        logger.info(f"总计处理: {total_count} 只股票")
        logger.info(f"成功更新: {success_count} 只股票")
        logger.info(f"跳过（无数据）: {total_count - success_count} 只股票")
        logger.info("=" * 80)
        
        return True
        
    except Exception as e:
        logger.error(f"初始化修复失败: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    logger = get_logger(__name__)
    
    success = fix_null_stock_date_ranges()
    
    if success:
        logger.info("✓ 初始化修复成功")
        sys.exit(0)
    else:
        logger.error("✗ 初始化修复失败")
        sys.exit(1)
