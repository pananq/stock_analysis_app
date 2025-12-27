#!/usr/bin/env python3
"""
清理DuckDB数据库中的数据
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.utils import get_config, get_logger
from app.models.duckdb_manager import DuckDBManager

logger = get_logger(__name__)


def clean_duckdb_data():
    """
    清理DuckDB数据库中的所有数据
    """
    logger.info("=" * 60)
    logger.info("开始清理DuckDB数据...")
    logger.info("=" * 60)
    
    # 获取配置
    config = get_config()
    duckdb_path = config.get('database.duckdb_path', './data/market_data.duckdb')
    
    # 转换为绝对路径
    if not os.path.isabs(duckdb_path):
        duckdb_path = os.path.join(project_root, duckdb_path)
    
    logger.info(f"DuckDB数据库路径: {duckdb_path}")
    
    # 检查数据库文件是否存在
    if not os.path.exists(duckdb_path):
        logger.warning(f"DuckDB数据库文件不存在: {duckdb_path}")
        logger.info("无需清理，退出")
        return
    
    # 创建DuckDB管理器
    try:
        duckdb = DuckDBManager(duckdb_path)
        
        # 查询清理前的数据量
        logger.info("\n检查清理前的数据...")
        try:
            count_result = duckdb.execute_query("SELECT COUNT(*) as count FROM daily_market")
            if count_result and count_result[0]:
                before_count = count_result[0]['count']
                logger.info(f"清理前数据量: {before_count} 条记录")
            else:
                logger.warning("无法查询数据量")
                before_count = 0
        except Exception as e:
            logger.warning(f"查询数据量失败: {e}")
            before_count = 0
        
        # 删除所有数据
        logger.info("\n正在删除数据...")
        try:
            duckdb.execute_update("DELETE FROM daily_market")
            logger.info("✓ daily_market表数据已清空")
        except Exception as e:
            logger.error(f"删除daily_market表数据失败: {e}")
            return
        
        # 查询清理后的数据量
        logger.info("\n检查清理后的数据...")
        try:
            count_result = duckdb.execute_query("SELECT COUNT(*) as count FROM daily_market")
            if count_result and count_result[0]:
                after_count = count_result[0]['count']
                logger.info(f"清理后数据量: {after_count} 条记录")
                
                if before_count > 0:
                    logger.info(f"已删除 {before_count - after_count} 条记录")
            else:
                logger.warning("无法查询数据量")
        except Exception as e:
            logger.warning(f"查询数据量失败: {e}")
        
        # 显示数据库文件大小
        try:
            file_size = os.path.getsize(duckdb_path)
            file_size_mb = file_size / (1024 * 1024)
            logger.info(f"\n数据库文件大小: {file_size_mb:.2f} MB")
            
            # 注意：DuckDB的DELETE操作不会立即回收空间，需要VACUUM
            logger.info("\n提示: DuckDB的DELETE操作不会立即回收磁盘空间")
            logger.info("如需回收空间，建议删除数据库文件或使用VACUUM命令")
        except Exception as e:
            logger.warning(f"查询文件大小失败: {e}")
        
        logger.info("\n" + "=" * 60)
        logger.info("DuckDB数据清理完成!")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"清理DuckDB数据失败: {e}")
        logger.info("\n" + "=" * 60)
        logger.info("DuckDB数据清理失败!")
        logger.info("=" * 60)
        raise


def delete_duckdb_file():
    """
    完全删除DuckDB数据库文件
    这个选项会删除整个数据库文件，包括表结构和数据
    """
    logger.info("=" * 60)
    logger.info("开始删除DuckDB数据库文件...")
    logger.info("=" * 60)
    
    # 获取配置
    config = get_config()
    duckdb_path = config.get('database.duckdb_path', './data/market_data.duckdb')
    
    # 转换为绝对路径
    if not os.path.isabs(duckdb_path):
        duckdb_path = os.path.join(project_root, duckdb_path)
    
    logger.info(f"DuckDB数据库路径: {duckdb_path}")
    
    # 检查数据库文件是否存在
    if not os.path.exists(duckdb_path):
        logger.warning(f"DuckDB数据库文件不存在: {duckdb_path}")
        logger.info("无需删除，退出")
        return
    
    try:
        # 获取文件大小
        file_size = os.path.getsize(duckdb_path)
        file_size_mb = file_size / (1024 * 1024)
        logger.info(f"数据库文件大小: {file_size_mb:.2f} MB")
        
        # 删除文件
        os.remove(duckdb_path)
        logger.info("✓ DuckDB数据库文件已删除")
        
        logger.info("\n" + "=" * 60)
        logger.info("DuckDB数据库文件删除完成!")
        logger.info("注意: 下次应用启动时会自动创建新的数据库文件")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"删除DuckDB数据库文件失败: {e}")
        logger.info("\n" + "=" * 60)
        logger.info("DuckDB数据库文件删除失败!")
        logger.info("=" * 60)
        raise


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='清理DuckDB数据库')
    parser.add_argument(
        '--delete-file',
        action='store_true',
        help='完全删除DuckDB数据库文件（包括表结构和数据）'
    )
    
    args = parser.parse_args()
    
    if args.delete_file:
        delete_duckdb_file()
    else:
        clean_duckdb_data()
