#!/usr/bin/env python3
"""
数据验证和一致性检查工具
用于验证SQLite到MySQL数据迁移的完整性和一致性
"""
import sys
import json
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.utils import get_logger
from app.models.sqlite_db import SQLiteDB
from app.models.mysql_db import MySQLDB
from app.utils.config import get_config

logger = get_logger(__name__)


class DataValidator:
    """数据验证工具类"""
    
    # 需要验证的表
    TABLES = [
        'stocks',
        'strategies',
        'strategy_results',
        'system_logs',
        'data_update_history',
        'job_logs',
        'task_execution_details'
    ]
    
    # 抽样验证的比例
    SAMPLE_RATIO = 0.1  # 10%
    MIN_SAMPLE_SIZE = 10  # 最少抽样数量
    
    def __init__(self, sqlite_path: str, mysql_config: Dict[str, Any]):
        """
        初始化验证工具
        
        Args:
            sqlite_path: SQLite数据库文件路径
            mysql_config: MySQL配置字典
        """
        self.sqlite_path = sqlite_path
        self.mysql_config = mysql_config
        self.sqlite_db = None
        self.mysql_db = None
        
        # 验证结果
        self.validation_result = {
            'tables': {},
            'overall': {
                'tables_checked': 0,
                'tables_passed': 0,
                'tables_failed': 0,
                'total_records_sqlite': 0,
                'total_records_mysql': 0,
                'total_mismatch': 0
            },
            'details': [],
            'validation_time': None
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
    
    def get_table_count(self, db: Any, table: str) -> int:
        """
        获取表的记录数
        
        Args:
            db: 数据库实例
            table: 表名
            
        Returns:
            记录数
        """
        query = f"SELECT COUNT(*) as count FROM {table}"
        result = db.execute_query(query)
        return result[0]['count'] if result else 0
    
    def validate_table_count(self, table: str) -> Dict[str, Any]:
        """
        验证表的记录数是否一致
        
        Args:
            table: 表名
            
        Returns:
            验证结果
        """
        logger.info(f"验证表 {table} 的记录数...")
        
        sqlite_count = self.get_table_count(self.sqlite_db, table)
        mysql_count = self.get_table_count(self.mysql_db, table)
        
        result = {
            'table': table,
            'sqlite_count': sqlite_count,
            'mysql_count': mysql_count,
            'count_match': sqlite_count == mysql_count,
            'diff': sqlite_count - mysql_count
        }
        
        if result['count_match']:
            logger.info(f"表 {table}: 记录数一致 ({sqlite_count})")
        else:
            logger.warning(f"表 {table}: 记录数不一致 SQLite={sqlite_count}, MySQL={mysql_count}")
        
        return result
    
    def sample_validate_table(self, table: str) -> Dict[str, Any]:
        """
        抽样验证表的数据内容
        
        Args:
            table: 表名
            
        Returns:
            验证结果
        """
        logger.info(f"抽样验证表 {table} 的数据内容...")
        
        result = {
            'table': table,
            'sample_size': 0,
            'sample_passed': 0,
            'sample_failed': 0,
            'mismatches': []
        }
        
        # 获取总记录数
        sqlite_count = self.get_table_count(self.sqlite_db, table)
        mysql_count = self.get_table_count(self.mysql_db, table)
        
        # 如果记录数不一致，跳过抽样验证
        if sqlite_count != mysql_count:
            logger.info(f"表 {table} 记录数不一致，跳过抽样验证")
            return result
        
        # 计算抽样数量
        sample_size = max(int(sqlite_count * self.SAMPLE_RATIO), self.MIN_SAMPLE_SIZE)
        sample_size = min(sample_size, sqlite_count)
        result['sample_size'] = sample_size
        
        # 获取SQLite抽样数据
        sqlite_query = f"SELECT * FROM {table} LIMIT {sample_size}"
        sqlite_data = self.sqlite_db.execute_query(sqlite_query)
        
        # 获取MySQL抽样数据
        mysql_query = f"SELECT * FROM {table} LIMIT {sample_size}"
        mysql_data = self.mysql_db.execute_query(mysql_query)
        
        # 逐条对比
        for i, (sqlite_record, mysql_record) in enumerate(zip(sqlite_data, mysql_data)):
            match, mismatch_details = self._compare_records(sqlite_record, mysql_record)
            
            if match:
                result['sample_passed'] += 1
            else:
                result['sample_failed'] += 1
                result['mismatches'].append({
                    'index': i,
                    'details': mismatch_details
                })
        
        logger.info(f"表 {table}: 抽样验证完成 通过={result['sample_passed']}, 失败={result['sample_failed']}")
        
        return result
    
    def _compare_records(self, record1: Dict[str, Any], record2: Dict[str, Any]) -> tuple:
        """
        对比两条记录是否一致
        
        Args:
            record1: 记录1
            record2: 记录2
            
        Returns:
            (是否一致, 差异详情)
        """
        mismatches = []
        
        # 检查字段是否一致
        keys1 = set(record1.keys())
        keys2 = set(record2.keys())
        
        if keys1 != keys2:
            mismatches.append(f"字段不一致: {keys1.symmetric_difference(keys2)}")
        
        # 检查字段值
        for key in keys1 & keys2:
            val1 = record1[key]
            val2 = record2[key]
            
            # 处理None值
            if val1 is None and val2 is None:
                continue
            
            # 处理字符串比较（去除空格）
            if isinstance(val1, str) and isinstance(val2, str):
                if val1.strip() != val2.strip():
                    mismatches.append(f"{key}: '{val1}' != '{val2}'")
                continue
            
            # 处理数字比较（浮点数精度）
            if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
                if abs(val1 - val2) > 0.0001:  # 允许小误差
                    mismatches.append(f"{key}: {val1} != {val2}")
                continue
            
            # 其他类型直接比较
            if val1 != val2:
                mismatches.append(f"{key}: {val1} != {val2}")
        
        return len(mismatches) == 0, mismatches
    
    def validate_all_tables(self) -> bool:
        """
        验证所有表的数据
        
        Returns:
            是否全部通过验证
        """
        self.validation_result['validation_time'] = datetime.now().isoformat()
        logger.info("=" * 60)
        logger.info("开始数据验证和一致性检查")
        logger.info("=" * 60)
        
        all_passed = True
        
        for table in self.TABLES:
            # 记录数验证
            count_result = self.validate_table_count(table)
            
            # 抽样验证
            sample_result = self.sample_validate_table(table)
            
            # 汇总结果
            table_passed = count_result['count_match'] and sample_result['sample_failed'] == 0
            
            self.validation_result['tables'][table] = {
                'count_validation': count_result,
                'sample_validation': sample_result,
                'passed': table_passed
            }
            
            # 更新总体统计
            self.validation_result['overall']['tables_checked'] += 1
            self.validation_result['overall']['total_records_sqlite'] += count_result['sqlite_count']
            self.validation_result['overall']['total_records_mysql'] += count_result['mysql_count']
            
            if count_result['diff'] != 0:
                self.validation_result['overall']['total_mismatch'] += abs(count_result['diff'])
            
            if table_passed:
                self.validation_result['overall']['tables_passed'] += 1
            else:
                self.validation_result['overall']['tables_failed'] += 1
                all_passed = False
            
            # 记录详情
            if not table_passed:
                self.validation_result['details'].append({
                    'table': table,
                    'count_diff': count_result['diff'],
                    'sample_failed': sample_result['sample_failed'],
                    'mismatches': sample_result['mismatches'][:5]  # 只保留前5个差异
                })
        
        self._print_summary()
        return all_passed
    
    def _print_summary(self):
        """打印验证摘要"""
        print("\n" + "=" * 60)
        print("数据验证结果摘要")
        print("=" * 60)
        
        overall = self.validation_result['overall']
        print(f"验证时间: {self.validation_result['validation_time']}")
        print(f"检查表数: {overall['tables_checked']}")
        print(f"通过表数: {overall['tables_passed']}")
        print(f"失败表数: {overall['tables_failed']}")
        print(f"SQLite总记录: {overall['total_records_sqlite']}")
        print(f"MySQL总记录: {overall['total_records_mysql']}")
        print(f"记录数差异: {overall['total_mismatch']}")
        
        print("\n各表验证结果:")
        for table, result in self.validation_result['tables'].items():
            status = "✓" if result['passed'] else "✗"
            count_match = result['count_validation']['count_match']
            sample_failed = result['sample_validation']['sample_failed']
            print(f"  {status} {table}: 记录数={'通过' if count_match else '失败'}, 抽样={'通过' if sample_failed == 0 else f'失败{sample_failed}'}")
        
        if self.validation_result['details']:
            print("\n失败详情:")
            for detail in self.validation_result['details']:
                print(f"  - {detail['table']}:")
                print(f"    记录数差异: {detail['count_diff']}")
                print(f"    抽样失败: {detail['sample_failed']}")
                if detail['mismatches']:
                    print(f"    差异数据: {detail['mismatches'][0]['details'][:100]}...")
        
        print("=" * 60)
    
    def save_report(self, output_path: str = None):
        """
        保存验证报告到文件
        
        Args:
            output_path: 输出文件路径
        """
        if output_path is None:
            output_dir = project_root / 'logs'
            output_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = output_dir / f'data_validation_report_{timestamp}.json'
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.validation_result, f, ensure_ascii=False, indent=2)
        
        logger.info(f"验证报告已保存到: {output_path}")
        print(f"\n验证报告已保存到: {output_path}")
    
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
    
    parser = argparse.ArgumentParser(description='数据验证和一致性检查工具')
    parser.add_argument('--sqlite-path', type=str, help='SQLite数据库文件路径（可选，默认使用配置文件中的路径）')
    parser.add_argument('--report', type=str, help='验证报告输出路径（可选）')
    
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
        
        # 创建验证工具实例
        validator = DataValidator(sqlite_path, mysql_config)
        
        # 初始化数据库
        validator.initialize_databases()
        
        # 执行验证
        all_passed = validator.validate_all_tables()
        
        # 保存报告
        validator.save_report(args.report)
        
        # 关闭连接
        validator.close()
        
        # 返回退出码
        sys.exit(0 if all_passed else 1)
        
    except KeyboardInterrupt:
        print("\n\n验证被用户中断")
        sys.exit(130)
    except Exception as e:
        logger.error(f"验证失败: {e}", exc_info=True)
        print(f"\n错误: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
