#!/usr/bin/env python3
"""
诊断脚本：检查当前数据库状态
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from app.utils import get_logger, setup_logging
from app.utils.config import get_config
from app.models.database_factory import DatabaseFactory


def check_database_state():
    """检查当前数据库状态"""
    logger = get_logger(__name__)
    
    try:
        # 加载配置
        config = get_config()
        
        # 初始化数据库
        db_factory = DatabaseFactory()
        database = db_factory.get_database(config=config.get('database.mysql'))
        
        logger.info("=" * 80)
        logger.info("当前数据库状态")
        logger.info("=" * 80)
        
        # 1. 统计各种情况的股票数量
        query = """
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN earliest_data_date IS NULL AND latest_data_date IS NULL THEN 1 ELSE 0 END) as both_null,
                SUM(CASE WHEN earliest_data_date IS NOT NULL AND latest_data_date IS NOT NULL THEN 1 ELSE 0 END) as both_not_null,
                SUM(CASE WHEN earliest_data_date IS NULL AND latest_data_date IS NOT NULL THEN 1 ELSE 0 END) as only_earliest_null,
                SUM(CASE WHEN earliest_data_date IS NOT NULL AND latest_data_date IS NULL THEN 1 ELSE 0 END) as only_latest_null
            FROM stocks
        """
        stats = database.execute_query(query)[0]
        
        logger.info(f"总股票数: {stats['total']}")
        logger.info(f"两个字段都为 NULL: {stats['both_null']}")
        logger.info(f"两个字段都有值: {stats['both_not_null']}")
        logger.info(f"只有 earliest_data_date 为 NULL: {stats['only_earliest_null']}")
        logger.info(f"只有 latest_data_date 为 NULL: {stats['only_latest_null']}")
        
        # 2. 查看一些具体的样本
        logger.info("\n" + "=" * 80)
        logger.info("部分更新样本（每个类别最多 3 只）")
        logger.info("=" * 80)
        
        # 只有 earliest_data_date 为 NULL 的样本
        query = """
            SELECT code, name, earliest_data_date, latest_data_date
            FROM stocks
            WHERE earliest_data_date IS NULL AND latest_data_date IS NOT NULL
            LIMIT 3
        """
        samples = database.execute_query(query)
        if samples:
            logger.info("\n只有 earliest_data_date 为 NULL:")
            for stock in samples:
                logger.info(f"  {stock['code']} - {stock['name']}: earliest={stock['earliest_data_date']}, latest={stock['latest_data_date']}")
        
        # 只有 latest_data_date 为 NULL 的样本
        query = """
            SELECT code, name, earliest_data_date, latest_data_date
            FROM stocks
            WHERE earliest_data_date IS NOT NULL AND latest_data_date IS NULL
            LIMIT 3
        """
        samples = database.execute_query(query)
        if samples:
            logger.info("\n只有 latest_data_date 为 NULL:")
            for stock in samples:
                logger.info(f"  {stock['code']} - {stock['name']}: earliest={stock['earliest_data_date']}, latest={stock['latest_data_date']}")
        
        logger.info("\n" + "=" * 80)
        
    except Exception as e:
        logger.error(f"检查失败: {e}", exc_info=True)


if __name__ == "__main__":
    # 加载配置并初始化日志系统
    config = get_config()
    setup_logging(config)
    
    logger = get_logger(__name__)
    
    check_database_state()
