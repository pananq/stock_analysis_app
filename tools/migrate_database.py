#!/usr/bin/env python3
"""
数据库迁移脚本 - 为stocks表添加earliest_data_date和latest_data_date字段
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.orm_db import ORMDBAdapter
from app.utils import get_logger, get_config
from datetime import datetime

logger = get_logger(__name__)


def migrate_database():
    """
    执行数据库迁移
    添加earliest_data_date和latest_data_date字段到stocks表
    """
    logger.info("=" * 60)
    logger.info("开始数据库迁移")
    logger.info("=" * 60)
    
    try:
        # 获取配置
        config = get_config()
        mysql_config = config.get('database.mysql')
        
        if not mysql_config:
            raise ValueError("未配置MySQL数据库信息")
        
        # 获取数据库实例
        db = ORMDBAdapter('mysql', mysql_config)
        
        # 检查字段是否已存在
        query = """
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = ? 
            AND TABLE_NAME = 'stocks' 
            AND COLUMN_NAME IN ('earliest_data_date', 'latest_data_date')
        """
        results = db.execute_query(query, (mysql_config.get('database'),))
        
        existing_columns = [row['COLUMN_NAME'] for row in results]
        logger.info(f"已存在的字段: {existing_columns}")
        
        # 添加字段
        if 'earliest_data_date' not in existing_columns:
            logger.info("添加字段: earliest_data_date")
            db.execute_update("""
                ALTER TABLE stocks 
                ADD COLUMN earliest_data_date DATE COMMENT '最早数据日期' 
                AFTER market_type
            """)
            logger.info("✓ earliest_data_date字段添加成功")
        else:
            logger.info("earliest_data_date字段已存在，跳过")
        
        if 'latest_data_date' not in existing_columns:
            logger.info("添加字段: latest_data_date")
            db.execute_update("""
                ALTER TABLE stocks 
                ADD COLUMN latest_data_date DATE COMMENT '最近数据日期' 
                AFTER earliest_data_date
            """)
            logger.info("✓ latest_data_date字段添加成功")
        else:
            logger.info("latest_data_date字段已存在，跳过")
        
        # 添加索引
        indexes_to_add = [
            ('idx_earliest_data_date', 'earliest_data_date'),
            ('idx_latest_data_date', 'latest_data_date')
        ]
        
        for index_name, column_name in indexes_to_add:
            # 检查索引是否已存在
            query = """
                SELECT INDEX_NAME 
                FROM INFORMATION_SCHEMA.STATISTICS 
                WHERE TABLE_SCHEMA = ? 
                AND TABLE_NAME = 'stocks' 
                AND INDEX_NAME = ?
            """
            index_exists = db.execute_query(query, (mysql_config.get('database'), index_name))
            
            if not index_exists:
                logger.info(f"添加索引: {index_name}")
                db.execute_update(f"""
                    CREATE INDEX {index_name} ON stocks({column_name})
                """)
                logger.info(f"✓ {index_name}索引添加成功")
            else:
                logger.info(f"{index_name}索引已存在，跳过")
        
        logger.info("=" * 60)
        logger.info("数据库迁移完成！")
        logger.info("=" * 60)
        return True
        
    except Exception as e:
        logger.error(f"数据库迁移失败: {e}", exc_info=True)
        logger.info("=" * 60)
        logger.info("数据库迁移失败！")
        logger.info("=" * 60)
        return False


def rollback_migration():
    """
    回滚数据库迁移
    删除earliest_data_date和latest_data_date字段（谨慎使用！）
    """
    logger.info("=" * 60)
    logger.info("开始回滚数据库迁移")
    logger.info("=" * 60)
    logger.warning("警告：此操作将删除earliest_data_date和latest_data_date字段！")
    
    try:
        # 获取配置
        config = get_config()
        mysql_config = config.get('database.mysql')
        
        if not mysql_config:
            raise ValueError("未配置MySQL数据库信息")
        
        # 获取数据库实例
        db = ORMDBAdapter('mysql', mysql_config)
        
        # 删除索引
        indexes_to_drop = ['idx_earliest_data_date', 'idx_latest_data_date']
        
        for index_name in indexes_to_drop:
            try:
                logger.info(f"删除索引: {index_name}")
                db.execute_update(f"""
                    ALTER TABLE stocks DROP INDEX {index_name}
                """)
                logger.info(f"✓ {index_name}索引删除成功")
            except Exception as e:
                logger.warning(f"索引{index_name}删除失败或不存在: {e}")
        
        # 删除字段
        columns_to_drop = ['latest_data_date', 'earliest_data_date']
        
        for column_name in columns_to_drop:
            try:
                logger.info(f"删除字段: {column_name}")
                db.execute_update(f"""
                    ALTER TABLE stocks DROP COLUMN {column_name}
                """)
                logger.info(f"✓ {column_name}字段删除成功")
            except Exception as e:
                logger.warning(f"字段{column_name}删除失败或不存在: {e}")
        
        logger.info("=" * 60)
        logger.info("数据库迁移回滚完成！")
        logger.info("=" * 60)
        return True
        
    except Exception as e:
        logger.error(f"数据库迁移回滚失败: {e}", exc_info=True)
        logger.info("=" * 60)
        logger.info("数据库迁移回滚失败！")
        logger.info("=" * 60)
        return False


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='数据库迁移工具')
    parser.add_argument('--rollback', action='store_true', help='回滚迁移（删除新增字段）')
    
    args = parser.parse_args()
    
    if args.rollback:
        success = rollback_migration()
    else:
        success = migrate_database()
    
    sys.exit(0 if success else 1)
