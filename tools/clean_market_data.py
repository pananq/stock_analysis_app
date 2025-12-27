#!/usr/bin/env python3
"""
清理MySQL数据库中的历史行情数据
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.utils import get_config, get_logger
from app.models.orm_models import DailyMarket, ORMDatabase

logger = get_logger(__name__)


def clean_market_data():
    """
    清理MySQL数据库中的历史行情数据
    """
    logger.info("=" * 60)
    logger.info("开始清理历史行情数据...")
    logger.info("=" * 60)
    
    // ... existing code ...
    
    # 获取配置
    config = get_config()
    mysql_config = config.get('database.mysql')
    
    if not mysql_config:
        logger.error("未配置MySQL数据库信息")
        return
    
    # 构建MySQL连接URL
    mysql_url = (
        f"mysql+pymysql://{mysql_config.get('username')}:"
        f"{mysql_config.get('password')}@"
        f"{mysql_config.get('host')}:"
        f"{mysql_config.get('port')}/"
        f"{mysql_config.get('database')}?charset=utf8mb4"
    )
    
    logger.info(f"MySQL数据库: {mysql_config.get('host')}:{mysql_config.get('port')}/{mysql_config.get('database')}")
    
    // ... existing code ...
    
    try:
        # 创建ORM数据库连接
        orm_db = ORMDatabase(mysql_url)
        session = orm_db.get_session()
        
        # 查询清理前的数据量
        logger.info("\n检查清理前的数据...")
        try:
            before_count = session.query(DailyMarket).count()
            logger.info(f"清理前数据量: {before_count} 条记录")
        except Exception as e:
            logger.warning(f"查询数据量失败: {e}")
            before_count = 0
        
        // ... existing code ...
        
        # 删除所有数据
        logger.info("\n正在删除数据...")
        try:
            deleted_count = session.query(DailyMarket).delete()
            session.commit()
            logger.info(f"✓ daily_market表数据已清空，删除了 {deleted_count} 条记录")
        except Exception as e:
            session.rollback()
            logger.error(f"删除daily_market表数据失败: {e}")
            return
        finally:
            session.close()
        
        // ... existing code ...
        
        # 查询清理后的数据量
        logger.info("\n检查清理后的数据...")
        session = orm_db.get_session()
        try:
            after_count = session.query(DailyMarket).count()
            logger.info(f"清理后数据量: {after_count} 条记录")
            
            if before_count > 0:
                logger.info(f"已删除 {before_count - after_count} 条记录")
        except Exception as e:
            logger.warning(f"查询数据量失败: {e}")
        finally:
            session.close()
        
        // ... existing code ...
        
        logger.info("\n" + "=" * 60)
        logger.info("历史行情数据清理完成!")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"清理历史行情数据失败: {e}")
        logger.info("\n" + "=" * 60)
        logger.info("历史行情数据清理失败!")
        logger.info("=" * 60)
        raise


def clean_by_stock_code(stock_code: str = None):
    """
    按股票代码清理数据
    
    Args:
        stock_code: 股票代码，如果为None则清理所有股票
    """
    logger.info("=" * 60)
    if stock_code:
        logger.info(f"开始清理股票 {stock_code} 的历史行情数据...")
    else:
        logger.info("开始清理所有股票的历史行情数据...")
    logger.info("=" * 60)
    
    // ... existing code ...
    
    # 获取配置
    config = get_config()
    mysql_config = config.get('database.mysql')
    
    if not mysql_config:
        logger.error("未配置MySQL数据库信息")
        return
    
    # 构建MySQL连接URL
    mysql_url = (
        f"mysql+pymysql://{mysql_config.get('username')}:"
        f"{mysql_config.get('password')}@"
        f"{mysql_config.get('host')}:"
        f"{mysql_config.get('port')}/"
        f"{mysql_config.get('database')}?charset=utf8mb4"
    )
    
    try:
        # 创建ORM数据库连接
        orm_db = ORMDatabase(mysql_url)
        session = orm_db.get_session()
        
        # 查询清理前的数据量
        logger.info("\n检查清理前的数据...")
        if stock_code:
            before_count = session.query(DailyMarket).filter(DailyMarket.code == stock_code).count()
            logger.info(f"股票 {stock_code} 清理前数据量: {before_count} 条记录")
        else:
            before_count = session.query(DailyMarket).count()
            logger.info(f"清理前数据量: {before_count} 条记录")
        
        // ... existing code ...
        
        # 删除数据
        logger.info("\n正在删除数据...")
        try:
            if stock_code:
                deleted_count = session.query(DailyMarket).filter(DailyMarket.code == stock_code).delete()
                logger.info(f"✓ 股票 {stock_code} 的数据已清空，删除了 {deleted_count} 条记录")
            else:
                deleted_count = session.query(DailyMarket).delete()
                logger.info(f"✓ 所有股票的数据已清空，删除了 {deleted_count} 条记录")
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"删除数据失败: {e}")
            return
        finally:
            session.close()
        
        // ... existing code ...
        
        # 查询清理后的数据量
        logger.info("\n检查清理后的数据...")
        session = orm_db.get_session()
        try:
            if stock_code:
                after_count = session.query(DailyMarket).filter(DailyMarket.code == stock_code).count()
                logger.info(f"股票 {stock_code} 清理后数据量: {after_count} 条记录")
            else:
                after_count = session.query(DailyMarket).count()
                logger.info(f"清理后数据量: {after_count} 条记录")
            
            if before_count > 0:
                logger.info(f"已删除 {before_count - after_count} 条记录")
        except Exception as e:
            logger.warning(f"查询数据量失败: {e}")
        finally:
            session.close()
        
        // ... existing code ...
        
        logger.info("\n" + "=" * 60)
        logger.info("历史行情数据清理完成!")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"清理历史行情数据失败: {e}")
        logger.info("\n" + "=" * 60)
        logger.info("历史行情数据清理失败!")
        logger.info("=" * 60)
        raise


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='清理历史行情数据')
    parser.add_argument(
        '--stock-code',
        type=str,
        help='只清理指定股票代码的数据（如果未指定则清理所有股票）'
    )
    
    args = parser.parse_args()
    
    if args.stock_code:
        clean_by_stock_code(args.stock_code)
    else:
        clean_market_data()
