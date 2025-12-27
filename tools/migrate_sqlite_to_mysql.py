#!/usr/bin/env python3
"""
SQLite到MySQL数据迁移工具
支持将SQLite数据库中的数据迁移到MySQL数据库
"""
import sys
import os
import shutil
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple
from datetime import datetime
from tqdm import tqdm

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.utils import get_logger
from app.models.sqlite_db import SQLiteDB
from app.models.mysql_db import MySQLDB
from app.utils.config import get_config

logger = get_logger(__name__)


class DatabaseMigrator:
    """数据库迁移工具类"""
    
    # 表迁移顺序（考虑外键依赖关系）
    TABLE_MIGRATION_ORDER = [
        'stocks',           # 独立表
        'strategies',       # 独立表
        'data_update_history',  # 独立表
        'strategy_results',  # 依赖strategies和stocks
        'job_logs',         # 独立表
        'task_execution_details',  # 依赖job_logs
        'system_logs',      # 独立表，最后迁移
    ]
    
    # 时间字段列表（需要格式转换）
    TIME_FIELDS = [
        'created_at', 'updated_at', 'last_executed_at',
        'timestamp', 'start_time', 'end_time', 'started_at', 'completed_at'
    ]
    
    def __init__(self, sqlite_path: str, mysql_config: Dict[str, Any]):
        """
        初始化迁移工具
        
        Args:
            sqlite_path: SQLite数据库文件路径
            mysql_config: MySQL配置字典
        """
        self.sqlite_path = sqlite_path
        self.mysql_config = mysql_config
        self.sqlite_db = None
        self.mysql_db = None
        
        # 迁移统计信息
        self.migration_stats = {
            'tables': {},
            'total_records': 0,
            'success_records': 0,
            'failed_records': 0,
            'start_time': None,
            'end_time': None,
            'errors': []
        }
    
    def initialize_databases(self):
        """初始化数据库连接"""
        logger.info("初始化数据库连接...")
        
        # 初始化SQLite
        self.sqlite_db = SQLiteDB(self.sqlite_path)
        logger.info(f"SQLite数据库连接成功: {self.sqlite_path}")
        
        # 初始化MySQL
        self.mysql_db = MySQLDB(self.mysql_config)
        logger.info(f"MySQL数据库连接成功: {self.mysql_config['host']}:{self.mysql_config['port']}/{self.mysql_config['database']}")
    
    def check_mysql_tables_empty(self) -> Tuple[bool, List[str]]:
        """
        检查MySQL表是否为空
        
        Returns:
            (是否全部为空, 有数据的表列表)
        """
        logger.info("检查MySQL表状态...")
        non_empty_tables = []
        
        for table in self.TABLE_MIGRATION_ORDER:
            query = f"SELECT COUNT(*) as count FROM {table}"
            result = self.mysql_db.execute_query(query)
            count = result[0]['count'] if result else 0
            
            if count > 0:
                non_empty_tables.append((table, count))
                logger.warning(f"MySQL表 {table} 已有 {count} 条数据")
        
        is_empty = len(non_empty_tables) == 0
        return is_empty, non_empty_tables
    
    def get_sqlite_table_data(self, table: str) -> List[Dict[str, Any]]:
        """
        从SQLite读取表数据
        
        Args:
            table: 表名
            
        Returns:
            表数据列表
        """
        query = f"SELECT * FROM {table}"
        return self.sqlite_db.execute_query(query)
    
    def convert_time_format(self, value: Any) -> str:
        """
        转换时间格式：SQLite -> MySQL
        
        Args:
            value: 时间值（可能是字符串、None等）
            
        Returns:
            MySQL DATETIME格式字符串
        """
        if value is None:
            return None
        
        if isinstance(value, str):
            # 尝试解析各种时间格式
            time_formats = [
                '%Y-%m-%d %H:%M:%S',           # 标准格式
                '%Y-%m-%dT%H:%M:%S',           # ISO格式
                '%Y-%m-%d %H:%M:%S.%f',        # 带毫秒
                '%Y-%m-%dT%H:%M:%S.%f',        # ISO带毫秒
                '%Y-%m-%d',                    # 只有日期
            ]
            
            for fmt in time_formats:
                try:
                    dt = datetime.strptime(value, fmt)
                    return dt.strftime('%Y-%m-%d %H:%M:%S')
                except ValueError:
                    continue
            
            # 如果都不匹配，尝试返回原值
            return value
        
        return value
    
    def convert_record(self, record: Dict[str, Any], table: str) -> Dict[str, Any]:
        """
        转换单条记录，处理数据类型和时间格式
        
        Args:
            record: 原始记录
            table: 表名
            
        Returns:
            转换后的记录
        """
        converted = {}
        
        for key, value in record.items():
            # 转换时间字段
            if key in self.TIME_FIELDS:
                value = self.convert_time_format(value)
            
            # 处理布尔值（SQLite用0/1存储）
            if key == 'enabled' and isinstance(value, int):
                converted[key] = bool(value)
            else:
                converted[key] = value
        
        return converted
    
    def migrate_table(self, table: str, overwrite: bool = False) -> Dict[str, int]:
        """
        迁移单个表的数据
        
        Args:
            table: 表名
            overwrite: 是否覆盖已有数据
            
        Returns:
            迁移统计信息
        """
        logger.info(f"开始迁移表: {table}")
        stats = {'total': 0, 'success': 0, 'failed': 0}
        
        # 如果不覆盖且表中有数据，跳过
        if not overwrite:
            query = f"SELECT COUNT(*) as count FROM {table}"
            result = self.mysql_db.execute_query(query)
            if result and result[0]['count'] > 0:
                logger.info(f"表 {table} 已有数据，跳过迁移（use --overwrite 强制覆盖）")
                return stats
        
        try:
            # 读取SQLite数据
            data = self.get_sqlite_table_data(table)
            stats['total'] = len(data)
            
            if stats['total'] == 0:
                logger.info(f"表 {table} 无数据，跳过")
                return stats
            
            # 清空现有数据（如果覆盖）
            if overwrite:
                self.mysql_db.execute_update(f"DELETE FROM {table}")
                logger.info(f"已清空表 {table} 的现有数据")
            
            # 批量插入
            batch_size = 1000
            batches = [data[i:i + batch_size] for i in range(0, len(data), batch_size)]
            
            with tqdm(total=len(data), desc=f"迁移 {table}", unit="条") as pbar:
                for batch in batches:
                    # 转换数据格式
                    converted_batch = [self.convert_record(record, table) for record in batch]
                    
                    try:
                        # 插入数据
                        for record in converted_batch:
                            columns = ', '.join(record.keys())
                            placeholders = ', '.join(['%s' for _ in record])
                            query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
                            self.mysql_db.execute_update(query, tuple(record.values()))
                            stats['success'] += 1
                            pbar.update(1)
                    
                    except Exception as e:
                        logger.error(f"批量插入失败: {e}")
                        stats['failed'] += len(batch)
                        self.migration_stats['errors'].append({
                            'table': table,
                            'error': str(e),
                            'batch_size': len(batch)
                        })
            
            logger.info(f"表 {table} 迁移完成: 成功 {stats['success']}, 失败 {stats['failed']}")
            
        except Exception as e:
            logger.error(f"迁移表 {table} 失败: {e}", exc_info=True)
            self.migration_stats['errors'].append({
                'table': table,
                'error': str(e)
            })
            stats['failed'] = stats['total']
        
        return stats
    
    def migrate_all_tables(self, overwrite: bool = False) -> bool:
        """
        迁移所有表
        
        Args:
            overwrite: 是否覆盖已有数据
            
        Returns:
            是否成功
        """
        self.migration_stats['start_time'] = datetime.now()
        logger.info("=" * 60)
        logger.info("开始SQLite到MySQL数据迁移")
        logger.info("=" * 60)
        
        # 检查MySQL表状态
        is_empty, non_empty_tables = self.check_mysql_tables_empty()
        if not is_empty and not overwrite:
            print("\n警告: 以下MySQL表已有数据:")
            for table, count in non_empty_tables:
                print(f"  - {table}: {count} 条")
            print("\n如需覆盖数据，请使用 --overwrite 参数")
            return False
        
        # 迁移每个表
        for table in self.TABLE_MIGRATION_ORDER:
            stats = self.migrate_table(table, overwrite)
            self.migration_stats['tables'][table] = stats
            self.migration_stats['total_records'] += stats['total']
            self.migration_stats['success_records'] += stats['success']
            self.migration_stats['failed_records'] += stats['failed']
        
        self.migration_stats['end_time'] = datetime.now()
        self._print_summary()
        
        return self.migration_stats['failed_records'] == 0
    
    def _print_summary(self):
        """打印迁移摘要"""
        duration = (self.migration_stats['end_time'] - self.migration_stats['start_time']).total_seconds()
        
        print("\n" + "=" * 60)
        print("迁移完成摘要")
        print("=" * 60)
        print(f"总耗时: {duration:.2f} 秒")
        print(f"总记录数: {self.migration_stats['total_records']}")
        print(f"成功: {self.migration_stats['success_records']}")
        print(f"失败: {self.migration_stats['failed_records']}")
        
        print("\n各表详情:")
        for table, stats in self.migration_stats['tables'].items():
            status = "✓" if stats['failed'] == 0 else "✗"
            print(f"  {status} {table}: 总计 {stats['total']}, 成功 {stats['success']}, 失败 {stats['failed']}")
        
        if self.migration_stats['errors']:
            print("\n错误详情:")
            for error in self.migration_stats['errors'][:10]:  # 只显示前10个错误
                print(f"  - {error['table']}: {error['error']}")
        
        print("=" * 60)
    
    def close(self):
        """关闭数据库连接"""
        if self.sqlite_db:
            logger.info("关闭SQLite连接")
        if self.mysql_db:
            self.mysql_db.close_all_connections()
            logger.info("关闭MySQL连接池")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='SQLite到MySQL数据迁移工具')
    parser.add_argument('--overwrite', action='store_true', help='覆盖MySQL中已有的数据')
    parser.add_argument('--sqlite-path', type=str, help='SQLite数据库文件路径（可选，默认使用配置文件中的路径）')
    
    args = parser.parse_args()
    
    try:
        # 获取配置
        config = get_config()
        
        # 获取SQLite路径
        sqlite_path = args.sqlite_path or config.get('database.sqlite_path')
        if not sqlite_path:
            print("错误: 未配置SQLite数据库路径")
            sys.exit(1)
        
        # 获取MySQL配置
        mysql_config = config.get('database.mysql')
        if not mysql_config:
            print("错误: 未配置MySQL数据库参数")
            sys.exit(1)
        
        # 创建迁移工具实例
        migrator = DatabaseMigrator(sqlite_path, mysql_config)
        
        # 初始化数据库
        migrator.initialize_databases()
        
        # 执行迁移
        success = migrator.migrate_all_tables(overwrite=args.overwrite)
        
        # 关闭连接
        migrator.close()
        
        # 返回退出码
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n迁移被用户中断")
        sys.exit(130)
    except Exception as e:
        logger.error(f"迁移失败: {e}", exc_info=True)
        print(f"\n错误: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
