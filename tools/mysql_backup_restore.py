#!/usr/bin/env python3
"""
MySQL 数据库备份和恢复工具
用途：从 config.yaml 读取 MySQL 配置，提供数据库备份和恢复功能
"""

import os
import sys
import yaml
import subprocess
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MySQLBackupRestore:
    """MySQL 数据库备份和恢复类"""
    
    def __init__(self, config_path: str = 'config.yaml', username: str = None, password: str = None):
        """
        初始化，从配置文件读取 MySQL 连接信息

        Args:
            config_path: 配置文件路径
            username: 数据库用户名（覆盖配置文件）
            password: 数据库密码（覆盖配置文件）
        """
        self.config_path = config_path
        self.mysql_config = self._load_mysql_config(username, password)
        self.backup_dir = self._get_backup_dir()

        # 确保备份目录存在
        os.makedirs(self.backup_dir, exist_ok=True)

        logger.info(f"MySQL 配置加载成功: {self.mysql_config['host']}:{self.mysql_config['port']}")
        logger.info(f"备份数据库: {self.mysql_config['database']}")
        logger.info(f"备份目录: {self.backup_dir}")
    
    def _load_mysql_config(self, username: str = None, password: str = None) -> dict:
        """从配置文件加载 MySQL 配置"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            mysql_config = config['database']['mysql']
            return {
                'host': mysql_config['host'],
                'port': mysql_config['port'],
                'database': mysql_config['database'],
                'username': username or mysql_config['username'],
                'password': password or mysql_config['password'],
                'charset': mysql_config.get('charset', 'utf8mb4')
            }
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            raise
    
    def _get_backup_dir(self) -> str:
        """获取备份目录"""
        # 从配置文件读取备份目录
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            backup_dir = config['data_management']['backup_dir']
            # 创建 mysql 子目录
            mysql_backup_dir = os.path.join(backup_dir, 'mysql')
            return mysql_backup_dir
        except Exception:
            # 默认备份目录
            return './data/backups/mysql'
    
    def _build_mysqldump_command(self, database: str = None, tables: List[str] = None) -> List[str]:
        """
        构建 mysqldump 命令
        
        Args:
            database: 数据库名称，默认为配置中的数据库
            tables: 表名列表，如果为 None 则备份整个数据库
            
        Returns:
            命令列表
        """
        db_name = database or self.mysql_config['database']
        
        cmd = [
            'mysqldump',
            f'--host={self.mysql_config["host"]}',
            f'--port={self.mysql_config["port"]}',
            f'--user={self.mysql_config["username"]}',
            f'--password={self.mysql_config["password"]}',
            f'--default-character-set={self.mysql_config["charset"]}',
            '--single-transaction',  # InnoDB 表，不锁定表
            '--routines',  # 包含存储过程和函数
            '--triggers',  # 包含触发器
            '--events',  # 包含事件
            '--quick',  # 一次检索一行
            '--lock-tables=false',  # 不锁定表
            '--flush-logs',  # 刷新日志
            '--hex-blob',  # 使用十六进制导出二进制数据
            db_name
        ]
        
        if tables:
            cmd.extend(tables)
        
        return cmd
    
    def _build_mysql_command(self, database: str = None) -> List[str]:
        """
        构建 mysql 命令
        
        Args:
            database: 数据库名称，默认为配置中的数据库
            
        Returns:
            命令列表
        """
        db_name = database or self.mysql_config['database']
        
        cmd = [
            'mysql',
            f'--host={self.mysql_config["host"]}',
            f'--port={self.mysql_config["port"]}',
            f'--user={self.mysql_config["username"]}',
            f'--password={self.mysql_config["password"]}',
            f'--default-character-set={self.mysql_config["charset"]}',
            db_name
        ]
        
        return cmd
    
    def backup(
        self,
        database: str = None,
        tables: List[str] = None,
        output_file: str = None,
        compress: bool = True
    ) -> str:
        """
        备份数据库或指定表
        
        Args:
            database: 数据库名称，默认为配置中的数据库
            tables: 表名列表，如果为 None 则备份整个数据库
            output_file: 输出文件路径，如果为 None 则自动生成
            compress: 是否压缩备份文件
            
        Returns:
            备份文件路径
        """
        db_name = database or self.mysql_config['database']
        
        # 生成备份文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if output_file is None:
            if tables:
                tables_str = '_'.join(tables)
                filename = f"{db_name}_{tables_str}_{timestamp}.sql"
            else:
                filename = f"{db_name}_{timestamp}.sql"
            
            if compress:
                filename += '.gz'
            
            output_file = os.path.join(self.backup_dir, filename)
        
        logger.info(f"开始备份: {db_name}")
        if tables:
            logger.info(f"备份表: {', '.join(tables)}")
        logger.info(f"输出文件: {output_file}")
        
        try:
            # 构建 mysqldump 命令
            cmd = self._build_mysqldump_command(database, tables)
            
            # 执行备份
            if compress:
                # 直接压缩输出
                output_mode = 'wb' if compress else 'w'
                with open(output_file, output_mode) as f:
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    
                    if compress:
                        import gzip
                        with gzip.open(f.name, 'wb') as gz:
                            for line in process.stdout:
                                gz.write(line)
                    else:
                        for line in process.stdout:
                            f.write(line.decode('utf-8'))
                    
                    _, stderr = process.communicate()
                    
                    if process.returncode != 0:
                        error_msg = stderr.decode('utf-8', errors='ignore')
                        logger.error(f"备份失败: {error_msg}")
                        raise subprocess.CalledProcessError(process.returncode, cmd, error_msg)
            else:
                with open(output_file, 'w', encoding='utf-8') as f:
                    subprocess.run(cmd, stdout=f, check=True, stderr=subprocess.PIPE)
            
            # 获取文件大小
            file_size = os.path.getsize(output_file)
            size_str = self._format_size(file_size)
            
            logger.info(f"备份成功: {output_file}")
            logger.info(f"文件大小: {size_str}")
            
            return output_file
            
        except subprocess.CalledProcessError as e:
            logger.error(f"备份失败: {e}")
            if os.path.exists(output_file):
                os.remove(output_file)
            raise
        except Exception as e:
            logger.error(f"备份异常: {e}")
            if os.path.exists(output_file):
                os.remove(output_file)
            raise
    
    def restore(
        self,
        backup_file: str,
        database: str = None,
        drop_database: bool = False,
        create_database: bool = False,
        tables: List[str] = None
    ) -> bool:
        """
        从备份文件恢复数据库
        
        Args:
            backup_file: 备份文件路径（.sql 或 .sql.gz）
            database: 数据库名称，默认为配置中的数据库
            drop_database: 是否先删除数据库
            create_database: 是否创建数据库
            tables: 如果指定，只恢复这些表
            
        Returns:
            是否成功
        """
        if not os.path.exists(backup_file):
            logger.error(f"备份文件不存在: {backup_file}")
            return False
        
        db_name = database or self.mysql_config['database']
        
        logger.info(f"开始恢复: {backup_file}")
        logger.info(f"目标数据库: {db_name}")
        
        try:
            # 删除数据库
            if drop_database:
                logger.warning(f"删除数据库: {db_name}")
                self._execute_sql(f"DROP DATABASE IF EXISTS `{db_name}`")
            
            # 创建数据库
            if create_database:
                logger.info(f"创建数据库: {db_name}")
                self._execute_sql(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET {self.mysql_config['charset']}")
            
            # 确定是否使用压缩文件
            is_gzipped = backup_file.endswith('.gz')
            
            # 构建恢复命令
            mysql_cmd = self._build_mysql_command(database)
            
            # 打开备份文件
            if is_gzipped:
                import gzip
                file_obj = gzip.open(backup_file, 'rb', encoding='utf-8')
            else:
                file_obj = open(backup_file, 'r', encoding='utf-8')
            
            # 执行恢复
            process = subprocess.Popen(
                mysql_cmd,
                stdin=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # 读取并写入 SQL
            if is_gzipped:
                for line in file_obj:
                    process.stdin.write(line)
            else:
                for line in file_obj:
                    process.stdin.write(line.encode('utf-8'))
            
            process.stdin.close()
            _, stderr = process.communicate()
            
            file_obj.close()
            
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8', errors='ignore')
                logger.error(f"恢复失败: {error_msg}")
                return False
            
            logger.info(f"恢复成功: {backup_file}")
            return True
            
        except Exception as e:
            logger.error(f"恢复异常: {e}")
            return False
    
    def _execute_sql(self, sql: str):
        """执行 SQL 命令（不指定数据库）"""
        cmd = [
            'mysql',
            f'--host={self.mysql_config["host"]}',
            f'--port={self.mysql_config["port"]}',
            f'--user={self.mysql_config["username"]}',
            f'--password={self.mysql_config["password"]}',
            f'--default-character-set={self.mysql_config["charset"]}',
            '-e', sql
        ]
        subprocess.run(cmd, check=True, stderr=subprocess.PIPE)
    
    def list_tables(self, database: str = None) -> List[str]:
        """
        列出数据库中的所有表
        
        Args:
            database: 数据库名称，默认为配置中的数据库
            
        Returns:
            表名列表
        """
        db_name = database or self.mysql_config['database']
        
        cmd = [
            'mysql',
            f'--host={self.mysql_config["host"]}',
            f'--port={self.mysql_config["port"]}',
            f'--user={self.mysql_config["username"]}',
            f'--password={self.mysql_config["password"]}',
            f'--default-character-set={self.mysql_config["charset"]}',
            '-e', f"USE {db_name}; SHOW TABLES;"
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            lines = result.stdout.strip().split('\n')
            # 跳过表头
            if len(lines) > 1:
                return lines[1:]
            return []
        except subprocess.CalledProcessError as e:
            logger.error(f"获取表列表失败: {e}")
            return []
    
    def list_backups(self) -> List[dict]:
        """
        列出所有备份文件
        
        Returns:
            备份文件信息列表
        """
        backups = []
        
        if not os.path.exists(self.backup_dir):
            return backups
        
        for filename in os.listdir(self.backup_dir):
            if filename.endswith('.sql') or filename.endswith('.sql.gz'):
                filepath = os.path.join(self.backup_dir, filename)
                stat = os.stat(filepath)
                
                backups.append({
                    'filename': filename,
                    'filepath': filepath,
                    'size': stat.st_size,
                    'size_str': self._format_size(stat.st_size),
                    'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                })
        
        # 按修改时间倒序排序
        backups.sort(key=lambda x: x['modified'], reverse=True)
        
        return backups
    
    def _format_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"
    
    def cleanup_old_backups(self, keep_count: int = 5):
        """
        清理旧备份
        
        Args:
            keep_count: 保留的备份数量
        """
        backups = self.list_backups()
        
        if len(backups) <= keep_count:
            logger.info(f"当前有 {len(backups)} 个备份，无需清理")
            return
        
        # 删除旧备份
        to_delete = backups[keep_count:]
        for backup in to_delete:
            try:
                os.remove(backup['filepath'])
                logger.info(f"删除旧备份: {backup['filename']}")
            except Exception as e:
                logger.error(f"删除失败: {backup['filename']}, 错误: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='MySQL 数据库备份和恢复工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 备份整个数据库
  python mysql_backup_restore.py backup

  # 使用自定义用户名备份
  python mysql_backup_restore.py backup --username admin

  # 使用交互式密码输入
  python mysql_backup_restore.py backup -p

  # 备份指定表
  python mysql_backup_restore.py backup --tables users stocks

  # 备份到指定文件
  python mysql_backup_restore.py backup --output /path/to/backup.sql.gz

  # 列出所有备份
  python mysql_backup_restore.py list

  # 恢复数据库
  python mysql_backup_restore.py restore --backup backup.sql.gz

  # 恢复并重建数据库（使用自定义凭据）
  python mysql_backup_restore.py restore --backup backup.sql.gz --drop --create -u root -p

  # 列出数据库中的表
  python mysql_backup_restore.py tables

  # 清理旧备份
  python mysql_backup_restore.py cleanup --keep 3
        """
    )
    
    # 全局参数
    parser.add_argument(
        '--config', '-c',
        default='config.yaml',
        help='配置文件路径 (默认: config.yaml)'
    )
    parser.add_argument(
        '--username', '-u',
        help='数据库用户名（覆盖配置文件中的设置）'
    )
    parser.add_argument(
        '--password', '-p',
        action='store_true',
        help='交互式输入数据库密码（覆盖配置文件中的设置）'
    )
    
    # 子命令
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # 备份命令
    backup_parser = subparsers.add_parser('backup', help='备份数据库')
    backup_parser.add_argument(
        '--database', '-d',
        help='数据库名称（默认使用配置文件中的数据库）'
    )
    backup_parser.add_argument(
        '--tables', '-t',
        nargs='+',
        help='要备份的表名列表（空格分隔）'
    )
    backup_parser.add_argument(
        '--output', '-o',
        help='输出文件路径（默认自动生成）'
    )
    backup_parser.add_argument(
        '--no-compress',
        action='store_true',
        help='不压缩备份文件'
    )
    
    # 恢复命令
    restore_parser = subparsers.add_parser('restore', help='从备份恢复数据库')
    restore_parser.add_argument(
        '--backup', '-b',
        required=True,
        help='备份文件路径'
    )
    restore_parser.add_argument(
        '--database', '-d',
        help='数据库名称（默认使用配置文件中的数据库）'
    )
    restore_parser.add_argument(
        '--drop',
        action='store_true',
        help='恢复前删除数据库'
    )
    restore_parser.add_argument(
        '--create',
        action='store_true',
        help='创建数据库'
    )
    restore_parser.add_argument(
        '--tables', '-t',
        nargs='+',
        help='只恢复这些表'
    )
    
    # 列出备份
    subparsers.add_parser('list', help='列出所有备份')
    
    # 列出表
    tables_parser = subparsers.add_parser('tables', help='列出数据库中的表')
    tables_parser.add_argument(
        '--database', '-d',
        help='数据库名称'
    )
    
    # 清理备份
    cleanup_parser = subparsers.add_parser('cleanup', help='清理旧备份')
    cleanup_parser.add_argument(
        '--keep', '-k',
        type=int,
        default=5,
        help='保留的备份数量（默认: 5）'
    )
    
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        # 处理交互式密码输入
        password = None
        if hasattr(args, 'password') and args.password:
            import getpass
            password = getpass.getpass("请输入数据库密码: ")

        # 创建备份恢复工具实例
        tool = MySQLBackupRestore(
            args.config,
            username=args.username if hasattr(args, 'username') else None,
            password=password
        )
        
        # 执行命令
        if args.command == 'backup':
            output_file = tool.backup(
                database=args.database,
                tables=args.tables,
                output_file=args.output,
                compress=not args.no_compress
            )
            print(f"\n✓ 备份成功: {output_file}")
        
        elif args.command == 'restore':
            success = tool.restore(
                backup_file=args.backup,
                database=args.database,
                drop_database=args.drop,
                create_database=args.create,
                tables=args.tables
            )
            if success:
                print(f"\n✓ 恢复成功")
            else:
                print(f"\n✗ 恢复失败")
                sys.exit(1)
        
        elif args.command == 'list':
            backups = tool.list_backups()
            if not backups:
                print("没有找到备份文件")
                return
            
            print("\n" + "=" * 100)
            print(f"{'文件名':<50} {'大小':<12} {'修改时间':<20}")
            print("=" * 100)
            for backup in backups:
                print(f"{backup['filename']:<50} {backup['size_str']:<12} {backup['modified']:<20}")
            print("=" * 100)
            print(f"总计: {len(backups)} 个备份文件")
        
        elif args.command == 'tables':
            tables = tool.list_tables(args.database)
            if not tables:
                print("没有找到表")
                return
            
            print(f"\n数据库中的表 ({len(tables)} 个):")
            for table in tables:
                print(f"  - {table}")
        
        elif args.command == 'cleanup':
            tool.cleanup_old_backups(args.keep)
            print(f"\n✓ 清理完成，保留最近 {args.keep} 个备份")
    
    except Exception as e:
        logger.error(f"执行失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
