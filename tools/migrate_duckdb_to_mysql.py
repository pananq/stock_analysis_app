#!/usr/bin/env python3
"""
DuckDB到MySQL数据迁移工具
将历史行情数据从DuckDB迁移到MySQL数据库
"""
import sys
import os
import argparse
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any
import traceback

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import duckdb
from app.utils import get_logger
from app.models.orm_models import DailyMarket, ORMDatabase
from app.utils.config import get_config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


class MigrationStats:
    """迁移统计信息"""
    
    def __init__(self):
        self.total_records = 0
        self.successful_inserts = 0
        self.skipped_records = 0
        self.failed_records = 0
        self.start_time = None
        self.end_time = None
        self.batch_count = 0
        self.errors = []
    
    def start(self):
        """开始计时"""
        self.start_time = datetime.now()
    
    def end(self):
        """结束计时"""
        self.end_time = datetime.now()
    
    def get_duration(self) -> float:
        """获取耗时（秒）"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'total_records': self.total_records,
            'successful_inserts': self.successful_inserts,
            'skipped_records': self.skipped_records,
            'failed_records': self.failed_records,
            'batch_count': self.batch_count,
            'duration_seconds': self.get_duration(),
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'errors_count': len(self.errors),
        }
    
    def print_summary(self):
        """打印统计摘要"""
        duration = self.get_duration()
        print("\n" + "="*60)
        print("迁移统计摘要")
        print("="*60)
        print(f"总记录数: {self.total_records}")
        print(f"成功插入: {self.successful_inserts}")
        print(f"跳过记录: {self.skipped_records}")
        print(f"失败记录: {self.failed_records}")
        print(f"批次数: {self.batch_count}")
        print(f"耗时: {duration:.2f} 秒")
        if self.total_records > 0:
            speed = self.total_records / duration if duration > 0 else 0
            print(f"速度: {speed:.0f} 条/秒")
        print("="*60)


class DuckDBToMySQLMigrator:
    """DuckDB到MySQL的迁移器"""
    
    def __init__(self, duckdb_path: str, mysql_url: str, batch_size: int = 1000, dry_run: bool = False):
        """
        初始化迁移器
        
        Args:
            duckdb_path: DuckDB数据库文件路径
            mysql_url: MySQL连接URL
            batch_size: 批量处理大小
            dry_run: 是否为模拟运行
        """
        self.duckdb_path = duckdb_path
        self.mysql_url = mysql_url
        self.batch_size = batch_size
        self.dry_run = dry_run
        self.logger = get_logger(__name__)
        self.stats = MigrationStats()
        
        # 创建MySQL引擎和会话
        self.mysql_engine = create_engine(mysql_url)
        self.Session = sessionmaker(bind=self.mysql_engine)
        
        # 验证DuckDB文件存在
        if not Path(duckdb_path).exists():
            raise FileNotFoundError(f"DuckDB文件不存在: {duckdb_path}")
    
    def get_duckdb_total_count(self) -> int:
        """获取DuckDB中daily_market表的总记录数"""
        conn = duckdb.connect(self.duckdb_path)
        try:
            result = conn.execute("SELECT COUNT(*) as count FROM daily_market").fetchone()
            return result[0] if result else 0
        finally:
            conn.close()
    
    def get_duckdb_stock_count(self) -> int:
        """获取DuckDB中股票数量"""
        conn = duckdb.connect(self.duckdb_path)
        try:
            result = conn.execute("SELECT COUNT(DISTINCT code) as count FROM daily_market").fetchone()
            return result[0] if result else 0
        finally:
            conn.close()
    
    def get_duckdb_date_range(self) -> Tuple[str, str]:
        """获取DuckDB中数据的日期范围"""
        conn = duckdb.connect(self.duckdb_path)
        try:
            result = conn.execute("""
                SELECT 
                    MIN(trade_date) as min_date,
                    MAX(trade_date) as max_date
                FROM daily_market
            """).fetchone()
            if result and result[0]:
                return str(result[0]), str(result[1])
            return None, None
        finally:
            conn.close()
    
    def read_duckdb_data(self, offset: int = 0, limit: int = None) -> List[Dict[str, Any]]:
        """
        从DuckDB读取数据
        
        Args:
            offset: 偏移量
            limit: 限制数量
            
        Returns:
            数据列表
        """
        conn = duckdb.connect(self.duckdb_path)
        try:
            query = "SELECT * FROM daily_market ORDER BY code, trade_date"
            params = []
            
            if limit is not None:
                query += " LIMIT ? OFFSET ?"
                params = [limit, offset]
            
            result = conn.execute(query, params)
            
            # 获取列名
            columns = [desc[0] for desc in result.description]
            
            # 转换为字典列表
            data = []
            for row in result.fetchall():
                row_dict = dict(zip(columns, row))
                # 转换Decimal类型为float
                for key in ['open', 'close', 'high', 'low', 'amount', 'change_pct', 'turnover_rate']:
                    if row_dict.get(key) is not None:
                        row_dict[key] = float(row_dict[key])
                data.append(row_dict)
            
            return data
        finally:
            conn.close()
    
    def insert_to_mysql(self, data: List[Dict[str, Any]]) -> Tuple[int, int]:
        """
        批量插入数据到MySQL
        
        Args:
            data: 数据列表
            
        Returns:
            (成功插入数, 跳过数)
        """
        if not data:
            return 0, 0
        
        session = self.Session()
        try:
            inserted_count = 0
            skipped_count = 0
            
            for record in data:
                try:
                    # 检查记录是否已存在
                    exists = session.query(DailyMarket).filter(
                        DailyMarket.code == record['code'],
                        DailyMarket.trade_date == record['trade_date']
                    ).first()
                    
                    if exists:
                        skipped_count += 1
                    else:
                        # 创建新记录
                        daily_market = DailyMarket(
                            code=record['code'],
                            trade_date=record['trade_date'],
                            open=record.get('open'),
                            close=record.get('close'),
                            high=record.get('high'),
                            low=record.get('low'),
                            volume=record.get('volume'),
                            amount=record.get('amount'),
                            change_pct=record.get('change_pct'),
                            turnover_rate=record.get('turnover_rate'),
                            created_at=record.get('created_at', datetime.now())
                        )
                        session.add(daily_market)
                        inserted_count += 1
                except Exception as e:
                    self.stats.errors.append(f"处理记录失败: {record.get('code', 'N/A')} {record.get('trade_date', 'N/A')}: {str(e)}")
                    self.stats.failed_records += 1
            
            session.commit()
            return inserted_count, skipped_count
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    def get_mysql_stats(self) -> Dict[str, Any]:
        """获取MySQL中的统计信息"""
        session = self.Session()
        try:
            # 总记录数
            total_count = session.query(DailyMarket).count()
            
            # 股票数量
            stock_count = session.query(DailyMarket.code).distinct().count()
            
            # 日期范围
            from sqlalchemy import func
            date_range = session.query(
                func.min(DailyMarket.trade_date),
                func.max(DailyMarket.trade_date)
            ).first()
            
            return {
                'total_count': total_count,
                'stock_count': stock_count,
                'min_date': str(date_range[0]) if date_range[0] else None,
                'max_date': str(date_range[1]) if date_range[1] else None,
            }
        finally:
            session.close()
    
    def backup_duckdb(self):
        """备份DuckDB数据库文件"""
        backup_path = self.duckdb_path + '.backup'
        shutil.copy2(self.duckdb_path, backup_path)
        self.logger.info(f"DuckDB数据库已备份到: {backup_path}")
        print(f"✓ DuckDB数据库已备份到: {backup_path}")
        return backup_path
    
    def validate_data(self) -> bool:
        """验证数据一致性"""
        print("\n" + "="*60)
        print("数据验证")
        print("="*60)
        
        # DuckDB统计
        duckdb_total = self.get_duckdb_total_count()
        duckdb_stocks = self.get_duckdb_stock_count()
        duckdb_min_date, duckdb_max_date = self.get_duckdb_date_range()
        
        print(f"\nDuckDB统计:")
        print(f"  总记录数: {duckdb_total}")
        print(f"  股票数量: {duckdb_stocks}")
        print(f"  日期范围: {duckdb_min_date} ~ {duckdb_max_date}")
        
        # MySQL统计
        mysql_stats = self.get_mysql_stats()
        print(f"\nMySQL统计:")
        print(f"  总记录数: {mysql_stats['total_count']}")
        print(f"  股票数量: {mysql_stats['stock_count']}")
        print(f"  日期范围: {mysql_stats['min_date']} ~ {mysql_stats['max_date']}")
        
        # 比较验证
        print(f"\n验证结果:")
        is_valid = True
        
        if duckdb_total != mysql_stats['total_count']:
            print(f"  ✗ 记录数不一致: DuckDB={duckdb_total}, MySQL={mysql_stats['total_count']}")
            is_valid = False
        else:
            print(f"  ✓ 记录数一致: {duckdb_total}")
        
        if duckdb_stocks != mysql_stats['stock_count']:
            print(f"  ✗ 股票数量不一致: DuckDB={duckdb_stocks}, MySQL={mysql_stats['stock_count']}")
            is_valid = False
        else:
            print(f"  ✓ 股票数量一致: {duckdb_stocks}")
        
        if duckdb_min_date != mysql_stats['min_date'] or duckdb_max_date != mysql_stats['max_date']:
            print(f"  ✗ 日期范围不一致")
            is_valid = False
        else:
            print(f"  ✓ 日期范围一致: {duckdb_min_date} ~ {duckdb_max_date}")
        
        return is_valid
    
    def migrate(self):
        """执行数据迁移"""
        self.stats.start()
        
        print("\n" + "="*60)
        print("开始数据迁移")
        print("="*60)
        print(f"DuckDB路径: {self.duckdb_path}")
        print(f"MySQL URL: {self.mysql_url}")
        print(f"批量大小: {self.batch_size}")
        print(f"模拟运行: {'是' if self.dry_run else '否'}")
        
        # 获取总记录数
        total_count = self.get_duckdb_total_count()
        self.stats.total_records = total_count
        
        print(f"\nDuckDB中待迁移记录总数: {total_count}")
        
        if total_count == 0:
            print("没有数据需要迁移")
            self.stats.end()
            return
        
        # 备份DuckDB文件
        if not self.dry_run:
            self.backup_duckdb()
        else:
            print("\n[DRY RUN] 跳过备份步骤")
        
        # 批量迁移
        print(f"\n开始批量迁移...")
        offset = 0
        batch_num = 0
        
        while offset < total_count:
            batch_num += 1
            self.stats.batch_count = batch_num
            
            # 读取数据
            data = self.read_duckdb_data(offset, self.batch_size)
            
            if self.dry_run:
                # 模拟运行，只统计不插入
                self.stats.successful_inserts += len(data)
                print(f"[DRY RUN] 批次 {batch_num}: 读取 {len(data)} 条记录 (偏移: {offset})")
            else:
                # 实际插入
                inserted, skipped = self.insert_to_mysql(data)
                self.stats.successful_inserts += inserted
                self.stats.skipped_records += skipped
                
                progress = (offset + len(data)) / total_count * 100
                print(f"批次 {batch_num}: 插入 {inserted} 条, 跳过 {skipped} 条 (进度: {progress:.1f}%)")
            
            offset += len(data)
        
        self.stats.end()
        
        # 打印统计
        self.stats.print_summary()
        
        # 数据验证
        if not self.dry_run:
            try:
                is_valid = self.validate_data()
                if is_valid:
                    print("\n✓ 数据迁移验证通过")
                else:
                    print("\n✗ 数据迁移验证失败，请检查日志")
            except Exception as e:
                print(f"\n✗ 数据验证失败: {str(e)}")
        else:
            print("\n[DRY RUN] 跳过数据验证")
        
        # 保存迁移报告
        self.save_migration_report()
    
    def save_migration_report(self):
        """保存迁移报告"""
        report_dir = Path(__file__).parent.parent / "logs"
        report_dir.mkdir(parents=True, exist_ok=True)
        
        report_file = report_dir / f"migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("="*60 + "\n")
            f.write("数据迁移报告\n")
            f.write("="*60 + "\n\n")
            f.write(f"迁移时间: {datetime.now().isoformat()}\n")
            f.write(f"DuckDB路径: {self.duckdb_path}\n")
            f.write(f"MySQL URL: {self.mysql_url}\n")
            f.write(f"批量大小: {self.batch_size}\n")
            f.write(f"模拟运行: {self.dry_run}\n\n")
            
            f.write("统计信息:\n")
            stats_dict = self.stats.to_dict()
            for key, value in stats_dict.items():
                f.write(f"  {key}: {value}\n")
            
            if self.stats.errors:
                f.write(f"\n错误信息 ({len(self.stats.errors)}):\n")
                for error in self.stats.errors[:100]:  # 最多保存100条错误
                    f.write(f"  - {error}\n")
        
        print(f"\n迁移报告已保存到: {report_file}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='DuckDB到MySQL数据迁移工具')
    parser.add_argument('--dry-run', action='store_true', help='模拟运行，不实际插入数据')
    parser.add_argument('--batch-size', type=int, default=1000, help='批量处理大小（默认: 1000）')
    parser.add_argument('--duckdb-path', type=str, help='DuckDB数据库文件路径（可选，默认使用配置文件中的路径）')
    parser.add_argument('--mysql-url', type=str, help='MySQL连接URL（可选，默认使用配置文件中的配置）')
    
    args = parser.parse_args()
    
    try:
        # 获取配置
        config = get_config()
        
        # 获取DuckDB路径
        if args.duckdb_path:
            duckdb_path = args.duckdb_path
        else:
            duckdb_path = config.get('database.duckdb_path')
            if not duckdb_path:
                print("错误: 未配置DuckDB数据库路径，请使用 --duckdb-path 参数指定")
                sys.exit(1)
        
        # 获取MySQL URL
        if args.mysql_url:
            mysql_url = args.mysql_url
        else:
            mysql_config = config.get('database.mysql')
            if not mysql_config:
                print("错误: 未配置MySQL数据库信息")
                sys.exit(1)
            
            mysql_url = (
                f"mysql+pymysql://{mysql_config.get('username')}:"
                f"{mysql_config.get('password')}@"
                f"{mysql_config.get('host')}:"
                f"{mysql_config.get('port')}/"
                f"{mysql_config.get('database')}?charset=utf8mb4"
            )
        
        # 创建迁移器并执行迁移
        migrator = DuckDBToMySQLMigrator(
            duckdb_path=duckdb_path,
            mysql_url=mysql_url,
            batch_size=args.batch_size,
            dry_run=args.dry_run
        )
        
        migrator.migrate()
        
        # 如果有错误，退出码为1
        if migrator.stats.failed_records > 0:
            sys.exit(1)
        
    except Exception as e:
        print(f"\n错误: {str(e)}")
        print("\n详细错误信息:")
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
