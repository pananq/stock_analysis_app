#!/usr/bin/env python3
"""
修复脚本：重新扫描并更新只更新了一个日期字段的股票
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


def fix_partial_updates():
    """修复只更新了一个字段的股票"""
    logger = get_logger(__name__)
    
    try:
        # 加载配置
        config = get_config()
        
        # 初始化数据库
        db_factory = DatabaseFactory()
        database = db_factory.get_database(config=config.get('database.mysql'))
        
        # 创建日期范围服务
        date_range_service = StockDateRangeService(database)
        
        logger.info("=" * 80)
        logger.info("开始修复只更新了一个日期字段的股票")
        logger.info("=" * 80)
        
        # 1. 查找只更新了一个字段的股票
        query = """
            SELECT code, name, earliest_data_date, latest_data_date
            FROM stocks
            WHERE (earliest_data_date IS NULL AND latest_data_date IS NOT NULL)
               OR (earliest_data_date IS NOT NULL AND latest_data_date IS NULL)
        """
        partial_stocks = database.execute_query(query)
        
        if not partial_stocks:
            logger.info("没有找到只更新了一个字段的股票")
            return True
        
        total_count = len(partial_stocks)
        logger.info(f"找到 {total_count} 只股票只更新了一个日期字段")
        
        # 2. 批量查询这些股票在 daily_market 表中的完整日期范围
        stock_codes = [stock['code'] for stock in partial_stocks]
        date_ranges = date_range_service.batch_get_stock_date_range_from_daily_market(stock_codes)
        
        # 3. 准备批量更新的数据
        updates = {}
        for stock in partial_stocks:
            stock_code = stock['code']
            stock_name = stock['name']
            current_earliest = stock.get('earliest_data_date')
            current_latest = stock.get('latest_data_date')
            
            earliest, latest = date_ranges.get(stock_code, (None, None))
            
            # 保留已有的值，只更新 NULL 的字段
            if earliest is None:
                earliest = current_earliest
            if latest is None:
                latest = current_latest
            
            # 确保两个都有值
            if earliest and latest:
                updates[stock_code] = (earliest, latest)
                logger.info(f"股票 {stock_code} - {stock_name}: 更新为 {earliest} ~ {latest}")
            else:
                logger.warning(f"股票 {stock_code} - {stock_name}: 无法获取完整的日期范围，跳过")
        
        if not updates:
            logger.warning("没有找到需要更新的股票")
            return True
        
        # 4. 批量更新
        success_count = date_range_service.batch_update_stock_date_ranges_optimized(updates)
        
        logger.info("=" * 80)
        logger.info(f"修复完成")
        logger.info(f"总计处理: {total_count} 只股票")
        logger.info(f"成功更新: {success_count} 只股票")
        logger.info(f"跳过: {total_count - success_count} 只股票")
        logger.info("=" * 80)
        
        return True
        
    except Exception as e:
        logger.error(f"修复失败: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    # 加载配置并初始化日志系统
    config = get_config()
    setup_logging(config)
    
    logger = get_logger(__name__)
    
    success = fix_partial_updates()
    
    if success:
        logger.info("✓ 修复成功")
        sys.exit(0)
    else:
        logger.error("✗ 修复失败")
        sys.exit(1)
