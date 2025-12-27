#!/usr/bin/env python3
"""
数据库初始化脚本
用于创建数据库表和初始化数据
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.orm_models import ORMDatabase, Base
from app.utils.config import get_config
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def init_database():
    """
    初始化数据库，创建所有表
    """
    logger.info("开始初始化数据库...")
    
    try:
        # 获取配置
        config = get_config()
        mysql_config = config.get('database.mysql')
        
        if not mysql_config:
            raise ValueError("未配置MySQL数据库信息")
        
        # 构建MySQL连接URL
        mysql_url = (
            f"mysql+pymysql://{mysql_config.get('username')}:"
            f"{mysql_config.get('password')}@"
            f"{mysql_config.get('host')}:"
            f"{mysql_config.get('port')}/"
            f"{mysql_config.get('database')}?charset=utf8mb4"
        )
        
        # 创建ORM数据库实例
        orm_db = ORMDatabase(mysql_url)
        
        # 获取引擎
        engine = orm_db.engine
        
        logger.info(f"连接到数据库: {mysql_config['database']}")
        
        # 创建所有表
        logger.info("正在创建数据库表...")
        Base.metadata.create_all(engine)
        
        logger.info("数据库表创建成功！")
        
        # 列出所有创建的表
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        logger.info(f"已创建的表: {', '.join(tables)}")
        
        # 检查daily_market表是否创建成功
        if 'daily_market' in tables:
            logger.info("✓ daily_market 表创建成功")
            
            # 检查索引
            indexes = inspector.get_indexes('daily_market')
            logger.info(f"✓ daily_market 表已创建 {len(indexes)} 个索引:")
            for idx in indexes:
                logger.info(f"  - {idx['name']}: {idx['column_names']}")
        else:
            logger.error("✗ daily_market 表创建失败")
            return False
        
        # 关闭连接
        engine.dispose()
        
        logger.info("数据库初始化完成！")
        return True
        
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """
    主函数
    """
    success = init_database()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
