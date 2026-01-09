#!/usr/bin/env python3
"""
诊断脚本：检查为什么会出现只更新一个日期字段的情况
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


def diagnose_partial_update():
    """诊断部分更新的问题"""
    logger = get_logger(__name__)
    
    try:
        # 加载配置
        config = get_config()
        
        # 初始化数据库
        db_factory = DatabaseFactory()
        database = db_factory.get_database(config=config.get('database.mysql'))
        
        logger.info("=" * 80)
        logger.info("开始诊断部分更新问题")
        logger.info("=" * 80)
        
        # 1. 查找只更新了一个字段的股票
        query = """
            SELECT code, name, earliest_data_date, latest_data_date
            FROM stocks
            WHERE (earliest_data_date IS NULL AND latest_data_date IS NOT NULL)
               OR (earliest_data_date IS NOT NULL AND latest_data_date IS NULL)
            LIMIT 10
        """
        partial_stocks = database.execute_query(query)
        
        logger.info(f"找到 {len(partial_stocks)} 只股票只更新了一个日期字段:")
        
        for stock in partial_stocks:
            stock_code = stock['code']
            stock_name = stock['name']
            earliest = stock.get('earliest_data_date')
            latest = stock.get('latest_data_date')
            
            logger.info(f"\n股票: {stock_code} - {stock_name}")
            logger.info(f"  earliest_data_date: {earliest}")
            logger.info(f"  latest_data_date: {latest}")
            
            # 2. 检查 daily_market 表中的数据
            query = f"""
                SELECT 
                    trade_date,
                    COUNT(*) as count,
                    MIN(trade_date) as min_date,
                    MAX(trade_date) as max_date
                FROM daily_market
                WHERE code = %s
                GROUP BY trade_date
                ORDER BY trade_date
                LIMIT 10
            """
            market_data = database.execute_query(query, (stock_code,))
            
            logger.info(f"  daily_market 表数据条数: {len(market_data)}")
            
            if market_data:
                # 查询真实的 MIN 和 MAX
                query = f"""
                    SELECT 
                        MIN(trade_date) as min_date,
                        MAX(trade_date) as max_date,
                        COUNT(*) as total_count,
                        COUNT(DISTINCT trade_date) as unique_dates
                    FROM daily_market
                    WHERE code = %s
                """
                summary = database.execute_query(query, (stock_code,))[0]
                
                logger.info(f"  MIN(trade_date): {summary.get('min_date')} (类型: {type(summary.get('min_date'))})")
                logger.info(f"  MAX(trade_date): {summary.get('max_date')} (类型: {type(summary.get('max_date'))})")
                logger.info(f"  总数据条数: {summary.get('total_count')}")
                logger.info(f"  唯一日期数: {summary.get('unique_dates')}")
                
                # 检查是否有 NULL 值
                query = f"""
                    SELECT COUNT(*) as null_count
                    FROM daily_market
                    WHERE code = %s AND trade_date IS NULL
                """
                null_check = database.execute_query(query, (stock_code,))
                logger.info(f"  NULL 值数量: {null_check[0].get('null_count')}")
        
        logger.info("\n" + "=" * 80)
        logger.info("诊断完成")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"诊断失败: {e}", exc_info=True)


if __name__ == "__main__":
    # 加载配置并初始化日志系统
    config = get_config()
    setup_logging(config)
    
    logger = get_logger(__name__)
    
    diagnose_partial_update()
