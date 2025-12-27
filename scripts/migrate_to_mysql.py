"""
数据库迁移脚本
将 SQLite 数据迁移到 MySQL（使用 ORM）
"""
import sys
import os
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils import get_logger
from app.models.orm_models import (
    Stock, Strategy, StrategyResult,
    SystemLog, DataUpdateHistory,
    JobLog, TaskExecutionDetail
)
from app.models.sqlite_db import SQLiteDB

logger = get_logger(__name__)


class DataMigrator:
    """数据迁移器"""
    
    def __init__(self, sqlite_db: SQLiteDB, mysql_db):
        """
        初始化迁移器
        
        Args:
            sqlite_db: SQLite数据库实例
            mysql_db: MySQL数据库实例（ORM）
        """
        self.sqlite_db = sqlite_db
        self.mysql_db = mysql_db
    
    def migrate_all(self):
        """迁移所有数据"""
        logger.info("=" * 60)
        logger.info("开始数据迁移: SQLite -> MySQL")
        logger.info("=" * 60)
        
        try:
            # 迁移各个表的数据
            self.migrate_stocks()
            self.migrate_strategies()
            self.migrate_strategy_results()
            self.migrate_system_logs()
            self.migrate_data_update_history()
            self.migrate_job_logs()
            self.migrate_task_execution_details()
            
            logger.info("=" * 60)
            logger.info("数据迁移完成！")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"数据迁移失败: {e}", exc_info=True)
            raise
    
    def migrate_stocks(self):
        """迁移股票数据"""
        logger.info("迁移股票数据...")
        
        # 从SQLite读取
        stocks = self.sqlite_db.execute_query("SELECT * FROM stocks")
        logger.info(f"  读取到 {len(stocks)} 条股票记录")
        
        # 写入MySQL（使用ORM）
        session = self.mysql_db.get_session()
        try:
            # 清空现有数据
            session.query(Stock).delete()
            session.commit()
            
            # 批量插入
            stock_objects = []
            for stock_data in stocks:
                # 转换日期格式
                stock_obj = Stock(
                    code=stock_data['code'],
                    name=stock_data['name'],
                    list_date=self._parse_date(stock_data.get('list_date')),
                    industry=stock_data.get('industry'),
                    market_type=stock_data.get('market_type'),
                    status=stock_data.get('status', 'normal'),
                    created_at=self._parse_datetime(stock_data.get('created_at')),
                    updated_at=self._parse_datetime(stock_data.get('updated_at'))
                )
                stock_objects.append(stock_obj)
            
            session.add_all(stock_objects)
            session.commit()
            
            logger.info(f"  成功迁移 {len(stock_objects)} 条股票记录")
            
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    def migrate_strategies(self):
        """迁移策略配置数据"""
        logger.info("迁移策略配置数据...")
        
        # 从SQLite读取
        strategies = self.sqlite_db.execute_query("SELECT * FROM strategies")
        logger.info(f"  读取到 {len(strategies)} 条策略记录")
        
        # 写入MySQL
        session = self.mysql_db.get_session()
        try:
            # 清空现有数据
            session.query(Strategy).delete()
            session.commit()
            
            # 批量插入
            strategy_objects = []
            for strategy_data in strategies:
                strategy_obj = Strategy(
                    name=strategy_data['name'],
                    description=strategy_data.get('description'),
                    config=strategy_data['config'],
                    enabled=bool(strategy_data.get('enabled', 1)),
                    created_at=self._parse_datetime(strategy_data.get('created_at')),
                    updated_at=self._parse_datetime(strategy_data.get('updated_at')),
                    last_executed_at=self._parse_datetime(strategy_data.get('last_executed_at'))
                )
                strategy_objects.append(strategy_obj)
            
            session.add_all(strategy_objects)
            session.commit()
            
            logger.info(f"  成功迁移 {len(strategy_objects)} 条策略记录")
            
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    def migrate_strategy_results(self):
        """迁移策略执行结果数据"""
        logger.info("迁移策略执行结果数据...")
        
        # 先获取MySQL中已存在的strategy_id和stock_code集合
        session = self.mysql_db.get_session()
        existing_strategy_ids = set()
        existing_stock_codes = set()
        try:
            strategies = session.query(Strategy).all()
            existing_strategy_ids = {strategy.id for strategy in strategies}
            
            stocks = session.query(Stock).all()
            existing_stock_codes = {stock.code for stock in stocks}
            
            logger.info(f"  MySQL中已存在的strategy_id: {len(existing_strategy_ids)} 个")
            logger.info(f"  MySQL中已存在的stock_code: {len(existing_stock_codes)} 个")
        finally:
            session.close()
        
        # 从SQLite读取
        results = self.sqlite_db.execute_query("SELECT * FROM strategy_results")
        logger.info(f"  读取到 {len(results)} 条策略结果记录")
        
        if not results:
            logger.info("  无数据需要迁移")
            return
        
        # 写入MySQL
        session = self.mysql_db.get_session()
        try:
            # 清空现有数据
            session.query(StrategyResult).delete()
            session.commit()
            
            # 批量插入（只插入有效的记录）
            result_objects = []
            skipped_count = 0
            
            for result_data in results:
                strategy_id = result_data['strategy_id']
                stock_code = result_data['stock_code']
                
                # 跳过引用不存在的strategy_id或stock_code的记录
                if strategy_id not in existing_strategy_ids or stock_code not in existing_stock_codes:
                    skipped_count += 1
                    continue
                
                result_obj = StrategyResult(
                    strategy_id=result_data['strategy_id'],
                    stock_code=result_data['stock_code'],
                    trigger_date=self._parse_date(result_data.get('trigger_date')),
                    trigger_price=result_data.get('trigger_price'),
                    rise_percent=result_data.get('rise_percent'),
                    result_data=result_data.get('result_data'),
                    executed_at=self._parse_datetime(result_data.get('executed_at'))
                )
                result_objects.append(result_obj)
            
            if result_objects:
                session.add_all(result_objects)
                session.commit()
                logger.info(f"  成功迁移 {len(result_objects)} 条策略结果记录")
                logger.info(f"  跳过 {skipped_count} 条无效记录")
            else:
                logger.info(f"  没有有效记录可以迁移（全部 {skipped_count} 条记录都被跳过）")
            
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    def migrate_system_logs(self):
        """迁移系统日志数据"""
        logger.info("迁移系统日志数据...")
        
        # 从SQLite读取
        logs = self.sqlite_db.execute_query("SELECT * FROM system_logs ORDER BY id DESC LIMIT 1000")
        logger.info(f"  读取到 {len(logs)} 条日志记录")
        
        if not logs:
            logger.info("  无数据需要迁移")
            return
        
        # 写入MySQL
        session = self.mysql_db.get_session()
        try:
            # 清空现有数据（可选，根据需求决定是否清空）
            # session.query(SystemLog).delete()
            # session.commit()
            
            # 批量插入
            log_objects = []
            for log_data in logs:
                log_obj = SystemLog(
                    timestamp=self._parse_datetime(log_data.get('timestamp')),
                    level=log_data['level'],
                    module=log_data['module'],
                    message=log_data['message'],
                    details=log_data.get('details')
                )
                log_objects.append(log_obj)
            
            session.add_all(log_objects)
            session.commit()
            
            logger.info(f"  成功迁移 {len(log_objects)} 条日志记录")
            
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    def migrate_data_update_history(self):
        """迁移数据更新历史数据"""
        logger.info("迁移数据更新历史数据...")
        
        # 从SQLite读取
        histories = self.sqlite_db.execute_query("SELECT * FROM data_update_history")
        logger.info(f"  读取到 {len(histories)} 条历史记录")
        
        if not histories:
            logger.info("  无数据需要迁移")
            return
        
        # 写入MySQL
        session = self.mysql_db.get_session()
        try:
            # 清空现有数据
            session.query(DataUpdateHistory).delete()
            session.commit()
            
            # 批量插入
            history_objects = []
            for history_data in histories:
                history_obj = DataUpdateHistory(
                    update_type=history_data['update_type'],
                    start_time=self._parse_datetime(history_data.get('start_time')),
                    end_time=self._parse_datetime(history_data.get('end_time')),
                    total_count=history_data.get('total_count', 0),
                    success_count=history_data.get('success_count', 0),
                    fail_count=history_data.get('fail_count', 0),
                    status=history_data.get('status', 'running'),
                    error_message=history_data.get('error_message')
                )
                history_objects.append(history_obj)
            
            session.add_all(history_objects)
            session.commit()
            
            logger.info(f"  成功迁移 {len(history_objects)} 条历史记录")
            
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    def migrate_job_logs(self):
        """迁移任务日志数据"""
        logger.info("迁移任务日志数据...")
        
        # 从SQLite读取
        job_logs = self.sqlite_db.execute_query("SELECT * FROM job_logs ORDER BY id DESC LIMIT 1000")
        logger.info(f"  读取到 {len(job_logs)} 条任务日志记录")
        
        if not job_logs:
            logger.info("  无数据需要迁移")
            return
        
        # 写入MySQL
        session = self.mysql_db.get_session()
        try:
            # 清空现有数据
            session.query(JobLog).delete()
            session.commit()
            
            # 批量插入
            job_log_objects = []
            for job_log_data in job_logs:
                job_log_obj = JobLog(
                    job_type=job_log_data['job_type'],
                    job_name=job_log_data['job_name'],
                    status=job_log_data['status'],
                    started_at=self._parse_datetime(job_log_data.get('started_at')),
                    completed_at=self._parse_datetime(job_log_data.get('completed_at')),
                    duration=job_log_data.get('duration'),
                    message=job_log_data.get('message'),
                    error=job_log_data.get('error')
                )
                job_log_objects.append(job_log_obj)
            
            session.add_all(job_log_objects)
            session.commit()
            
            logger.info(f"  成功迁移 {len(job_log_objects)} 条任务日志记录")
            
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    def migrate_task_execution_details(self):
        """迁移任务执行详细数据"""
        logger.info("迁移任务执行详细数据...")
        
        # 先获取MySQL中已存在的job_log_id集合
        session = self.mysql_db.get_session()
        existing_job_log_ids = set()
        try:
            job_logs = session.query(JobLog).all()
            existing_job_log_ids = {job.id for job in job_logs}
            logger.info(f"  MySQL中已存在的job_log_id: {len(existing_job_log_ids)} 个")
        finally:
            session.close()
        
        # 从SQLite读取
        details = self.sqlite_db.execute_query("SELECT * FROM task_execution_details ORDER BY id DESC LIMIT 1000")
        logger.info(f"  读取到 {len(details)} 条详细记录")
        
        if not details:
            logger.info("  无数据需要迁移")
            return
        
        # 写入MySQL
        session = self.mysql_db.get_session()
        try:
            # 清空现有数据
            session.query(TaskExecutionDetail).delete()
            session.commit()
            
            # 批量插入（只插入引用已存在的job_log_id的记录）
            detail_objects = []
            skipped_count = 0
            
            for detail_data in details:
                job_log_id = detail_data['job_log_id']
                
                # 跳过引用不存在的job_log_id的记录
                if job_log_id not in existing_job_log_ids:
                    skipped_count += 1
                    continue
                
                detail_obj = TaskExecutionDetail(
                    job_log_id=detail_data['job_log_id'],
                    task_type=detail_data['task_type'],
                    stock_code=detail_data.get('stock_code'),
                    stock_name=detail_data.get('stock_name'),
                    detail_type=detail_data['detail_type'],
                    detail_data=detail_data['detail_data'],
                    created_at=self._parse_datetime(detail_data.get('created_at'))
                )
                detail_objects.append(detail_obj)
            
            if detail_objects:
                session.add_all(detail_objects)
                session.commit()
                logger.info(f"  成功迁移 {len(detail_objects)} 条详细记录")
                logger.info(f"  跳过 {skipped_count} 条无效记录（引用不存在的job_log_id）")
            else:
                logger.info(f"  没有有效记录可以迁移（全部 {skipped_count} 条记录都被跳过）")
            
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    @staticmethod
    def _parse_date(date_str):
        """解析日期字符串"""
        if not date_str or date_str in ['None', '', 'null']:
            return None
        
        try:
            # 尝试解析各种日期格式
            if isinstance(date_str, datetime):
                return date_str.date()
            
            # YYYY-MM-DD
            if len(date_str) == 10:
                return datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # YYYY-MM-DD HH:MM:SS
            if len(date_str) == 19:
                return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S').date()
            
            return None
        except:
            return None
    
    @staticmethod
    def _parse_datetime(datetime_str):
        """解析日期时间字符串"""
        if not datetime_str or datetime_str in ['None', '', 'null']:
            return None
        
        try:
            if isinstance(datetime_str, datetime):
                return datetime_str
            
            # YYYY-MM-DD HH:MM:SS
            if len(datetime_str) == 19:
                return datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
            
            # YYYY-MM-DD
            if len(datetime_str) == 10:
                return datetime.strptime(datetime_str, '%Y-%m-%d')
            
            return None
        except:
            return None


def main():
    """主函数"""
    from app.utils import get_config
    from app.models.orm_db import ORMDBAdapter
    
    logger.info("初始化数据库连接...")
    
    # 获取配置
    config = get_config()
    
    # 初始化SQLite数据库
    sqlite_db_path = config.get('database.sqlite_path')
    sqlite_db = SQLiteDB(sqlite_db_path)
    
    # 初始化MySQL ORM数据库
    mysql_config = config.get('database.mysql')
    mysql_db = ORMDBAdapter('mysql', mysql_config)
    
    # 执行迁移
    migrator = DataMigrator(sqlite_db, mysql_db)
    migrator.migrate_all()
    
    logger.info("迁移完成！")


if __name__ == '__main__':
    main()
