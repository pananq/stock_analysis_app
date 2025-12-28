#!/usr/bin/env python3
"""
数据库迁移脚本：允许不同用户使用相同的策略名称

功能：
1. 检查并添加 user_id 字段到 strategies 表
2. 删除 name 的全局唯一索引
3. 添加 (name, user_id) 组合唯一索引
4. 添加外键约束和索引
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.utils import get_logger
from app.models.database_factory import get_database

logger = get_logger(__name__)


def migrate_strategy_table():
    """执行数据库迁移"""
    db = get_database()
    
    try:
        # 步骤1：检查是否已有 user_id 字段
        result = db.execute_query("SHOW COLUMNS FROM strategies LIKE 'user_id'")
        
        if not result:
            logger.info("strategies 表没有 user_id 字段，开始添加...")
            # 添加 user_id 字段
            db.execute_update(
                "ALTER TABLE strategies ADD COLUMN user_id INT NOT NULL DEFAULT 1 COMMENT '所属用户ID' AFTER id"
            )
            logger.info("user_id 字段添加成功")
        else:
            logger.info("strategies 表已有 user_id 字段，跳过添加")
        
        # 步骤2：删除全局的 name 唯一索引（如果存在）
        result = db.execute_query("SHOW INDEX FROM strategies WHERE Key_name = 'idx_name'")
        if result:
            logger.info("删除全局的 name 唯一索引...")
            db.execute_update("ALTER TABLE strategies DROP INDEX idx_name")
            logger.info("全局 name 唯一索引已删除")
        else:
            logger.info("未找到 idx_name 索引，跳过删除")
        
        # 步骤3：添加 (name, user_id) 组合唯一索引
        result = db.execute_query("SHOW INDEX FROM strategies WHERE Key_name = 'idx_name_user'")
        if not result:
            logger.info("添加 (name, user_id) 组合唯一索引...")
            db.execute_update("ALTER TABLE strategies ADD UNIQUE INDEX idx_name_user (name, user_id)")
            logger.info("(name, user_id) 组合唯一索引添加成功")
        else:
            logger.info("idx_name_user 索引已存在，跳过添加")
        
        # 步骤4：添加外键约束（如果不存在）
        result = db.execute_query("""
            SELECT CONSTRAINT_NAME 
            FROM information_schema.KEY_COLUMN_USAGE 
            WHERE TABLE_NAME = 'strategies' 
            AND CONSTRAINT_NAME = 'fk_strategies_user'
        """)
        if not result:
            logger.info("添加外键约束 fk_strategies_user...")
            try:
                db.execute_update(
                    "ALTER TABLE strategies ADD CONSTRAINT fk_strategies_user "
                    "FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE"
                )
                logger.info("外键约束添加成功")
            except Exception as e:
                logger.warning(f"添加外键约束失败（可能已存在外键或users表不存在）: {e}")
        else:
            logger.info("外键约束 fk_strategies_user 已存在，跳过添加")
        
        # 步骤5：添加 user_id 索引（如果不存在）
        result = db.execute_query("SHOW INDEX FROM strategies WHERE Key_name = 'idx_user_id'")
        if not result:
            logger.info("添加 user_id 索引...")
            db.execute_update("ALTER TABLE strategies ADD INDEX idx_user_id (user_id)")
            logger.info("user_id 索引添加成功")
        else:
            logger.info("idx_user_id 索引已存在，跳过添加")
        
        # 显示最终的表结构
        logger.info("\n迁移完成！strategies 表结构如下：")
        result = db.execute_query("DESCRIBE strategies")
        for row in result:
            logger.info(f"  {row['Field']}: {row['Type']} {'NOT NULL' if row['Null'] == 'NO' else 'NULL'}")
        
        logger.info("\n索引信息：")
        result = db.execute_query("SHOW INDEX FROM strategies")
        for row in result:
            logger.info(f"  {row['Key_name']}: {row['Column_name']} ({'Unique' if not row['Non_unique'] else 'Non-unique'})")
        
        logger.info("\n✅ 数据库迁移成功完成！")
        logger.info("\n现在不同用户可以使用相同的策略名称了。")
        logger.info("同一用户下的策略名称仍然必须唯一。")
        
        return True
        
    except Exception as e:
        logger.error(f"数据库迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("=" * 60)
    print("策略表迁移：允许不同用户使用相同的策略名称")
    print("=" * 60)
    print()
    
    success = migrate_strategy_table()
    
    print()
    print("=" * 60)
    if success:
        print("迁移成功！")
        sys.exit(0)
    else:
        print("迁移失败！请检查日志。")
        sys.exit(1)
