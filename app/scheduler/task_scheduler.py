"""
任务调度器

使用APScheduler实现定时任务调度，包括：
1. 每日更新股票列表
2. 每日更新行情数据
3. 自动执行启用的策略
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from app.services import (
    get_stock_service,
    get_market_data_service,
    get_strategy_service,
    get_strategy_executor
)
from app.models.database_factory import get_database
from app.utils import get_logger, get_config

logger = get_logger(__name__)


class TaskScheduler:
    """任务调度器"""
    
    def __init__(self):
        """初始化任务调度器"""
        self.scheduler = BackgroundScheduler()
        self.config = get_config()
        self.db = get_database()  # 使用工厂方法获取数据库（MySQL或SQLite）
        
        # 初始化数据库表
        self._init_database()
        
        # 服务实例
        self.stock_service = get_stock_service()
        self.market_data_service = get_market_data_service()
        self.strategy_service = get_strategy_service()
        self.strategy_executor = get_strategy_executor()
        
        # 添加事件监听器
        self.scheduler.add_listener(
            self._job_executed_listener,
            EVENT_JOB_EXECUTED | EVENT_JOB_ERROR
        )
        
        logger.info("任务调度器初始化完成")
    
    def _init_database(self):
        """初始化数据库表"""
        try:
            # MySQL使用AUTO_INCREMENT，INT类型
            create_table_sql = """
                CREATE TABLE IF NOT EXISTS job_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    job_type VARCHAR(50) NOT NULL,
                    job_name VARCHAR(200) NOT NULL,
                    status VARCHAR(20) NOT NULL,
                    started_at DATETIME NOT NULL,
                    completed_at DATETIME,
                    duration DECIMAL(10,3),
                    message TEXT,
                    error TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
            
            self.db.execute_update(create_table_sql)
            
            # MySQL不支持IF NOT EXISTS，需要先检查索引是否存在
            # 获取已存在的索引
            existing_indexes = self.db.execute_query(
                "SELECT index_name FROM information_schema.statistics "
                "WHERE table_schema = DATABASE() AND table_name = 'job_logs'"
            )
            # 处理返回结果，考虑列名可能的大小写问题
            index_names = []
            for idx in existing_indexes:
                if isinstance(idx, dict):
                    # 尝试不同的键名
                    for key in ['index_name', 'INDEX_NAME', 'Index_Name']:
                        if key in idx:
                            index_names.append(idx[key])
                            break
                elif isinstance(idx, (list, tuple)):
                    # 如果返回的是列表或元组，取第一个元素
                    index_names.append(idx[0])
            
            # 创建索引
            if 'idx_job_logs_started_at' not in index_names:
                self.db.execute_update(
                    "CREATE INDEX idx_job_logs_started_at ON job_logs(started_at)"
                )
            if 'idx_job_logs_status' not in index_names:
                self.db.execute_update(
                    "CREATE INDEX idx_job_logs_status ON job_logs(status)"
                )
            
            logger.info("任务日志数据库表初始化完成")
            
        except Exception as e:
            logger.error(f"初始化数据库表失败: {e}")
    
    def start(self):
        """启动调度器"""
        if not self.scheduler.running:
            # 启动前清理僵尸任务（状态为running但实际已停止的任务）
            self._cleanup_zombie_tasks()
            
            self.scheduler.start()
            logger.info("任务调度器已启动")
        else:
            logger.warning("任务调度器已经在运行中")
    
    def shutdown(self, wait: bool = True):
        """
        关闭调度器
        
        Args:
            wait: 是否等待所有任务完成
        """
        if self.scheduler.running:
            self.scheduler.shutdown(wait=wait)
            logger.info("任务调度器已关闭")
        else:
            logger.warning("任务调度器未运行")
    
    def add_daily_stock_update_job(self, hour: int = 18, minute: int = 0):
        """
        添加每日股票列表更新任务
        
        Args:
            hour: 执行小时（0-23）
            minute: 执行分钟（0-59）
        """
        try:
            # 使用cron触发器，每天指定时间执行
            trigger = CronTrigger(hour=hour, minute=minute)
            
            self.scheduler.add_job(
                func=self._update_stock_list_job,
                trigger=trigger,
                id='daily_stock_update',
                name='每日更新股票列表',
                replace_existing=True,
                max_instances=1
            )
            
            logger.info(f"已添加每日股票列表更新任务: {hour:02d}:{minute:02d}")
            
        except Exception as e:
            logger.error(f"添加每日股票列表更新任务失败: {e}")
    
    def add_daily_market_data_update_job(self, hour: int = 18, minute: int = 30):
        """
        添加每日行情数据更新任务
        
        Args:
            hour: 执行小时（0-23）
            minute: 执行分钟（0-59）
        """
        try:
            # 使用cron触发器，每天指定时间执行
            trigger = CronTrigger(hour=hour, minute=minute)
            
            self.scheduler.add_job(
                func=self._update_market_data_job,
                trigger=trigger,
                id='daily_market_data_update',
                name='每日更新行情数据',
                replace_existing=True,
                max_instances=1
            )
            
            logger.info(f"已添加每日行情数据更新任务: {hour:02d}:{minute:02d}")
            
        except Exception as e:
            logger.error(f"添加每日行情数据更新任务失败: {e}")
    
    def add_daily_strategy_execution_job(self, hour: int = 19, minute: int = 0):
        """
        添加每日策略执行任务
        
        Args:
            hour: 执行小时（0-23）
            minute: 执行分钟（0-59）
        """
        try:
            # 使用cron触发器，每天指定时间执行
            trigger = CronTrigger(hour=hour, minute=minute)
            
            self.scheduler.add_job(
                func=self._execute_strategies_job,
                trigger=trigger,
                id='daily_strategy_execution',
                name='每日执行策略',
                replace_existing=True,
                max_instances=1
            )
            
            logger.info(f"已添加每日策略执行任务: {hour:02d}:{minute:02d}")
            
        except Exception as e:
            logger.error(f"添加每日策略执行任务失败: {e}")
    
    def add_periodic_health_check_job(self, interval_minutes: int = 30):
        """
        添加定期健康检查任务
        
        Args:
            interval_minutes: 检查间隔（分钟）
        """
        try:
            # 使用间隔触发器
            trigger = IntervalTrigger(minutes=interval_minutes)
            
            self.scheduler.add_job(
                func=self._health_check_job,
                trigger=trigger,
                id='periodic_health_check',
                name='定期健康检查',
                replace_existing=True,
                max_instances=1
            )
            
            logger.info(f"已添加定期健康检查任务: 每{interval_minutes}分钟")
            
        except Exception as e:
            logger.error(f"添加定期健康检查任务失败: {e}")
    
    def run_job_now(self, job_id: str) -> bool:
        """
        立即执行指定任务
        
        Args:
            job_id: 任务ID
            
        Returns:
            是否成功触发
        """
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                job.modify(next_run_time=datetime.now())
                logger.info(f"已触发任务立即执行: {job_id}")
                return True
            else:
                logger.error(f"任务不存在: {job_id}")
                return False
                
        except Exception as e:
            logger.error(f"触发任务执行失败: {e}")
            return False
    
    def remove_job(self, job_id: str) -> bool:
        """
        移除指定任务
        
        Args:
            job_id: 任务ID
            
        Returns:
            是否成功移除
        """
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"已移除任务: {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"移除任务失败: {e}")
            return False
    
    def get_jobs(self) -> List[Dict[str, Any]]:
        """
        获取所有任务信息
        
        Returns:
            任务列表
        """
        jobs = []
        
        for job in self.scheduler.get_jobs():
            next_run_time = getattr(job, 'next_run_time', None)
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run_time': next_run_time.strftime('%Y-%m-%d %H:%M:%S') if next_run_time else None,
                'trigger': str(job.trigger)
            })
        
        return jobs
    
    def _update_stock_list_job(self):
        """更新股票列表任务"""
        logger.info("=" * 60)
        logger.info("开始执行: 更新股票列表")
        logger.info("=" * 60)
        
        start_time = datetime.now()
        
        try:
            # 记录任务开始
            self._log_job_start('update_stock_list', '更新股票列表')
            
            # 执行更新
            result = self.stock_service.update_stock_list()
            
            # 记录任务完成
            duration = (datetime.now() - start_time).total_seconds()
            
            if result['success']:
                self._log_job_success(
                    'update_stock_list',
                    duration,
                    f"新增: {result['added']}, 更新: {result['updated']}"
                )
                logger.info(f"✓ 股票列表更新成功: 新增{result['added']}只, 更新{result['updated']}只")
            else:
                self._log_job_error(
                    'update_stock_list',
                    duration,
                    result.get('error', '未知错误')
                )
                logger.error(f"✗ 股票列表更新失败: {result.get('error', '未知错误')}")
                
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            self._log_job_error('update_stock_list', duration, str(e))
            logger.error(f"✗ 股票列表更新异常: {e}")
            import traceback
            traceback.print_exc()
        
        logger.info("=" * 60)
    
    def _update_market_data_job(self):
        """更新行情数据任务"""
        logger.info("=" * 60)
        logger.info("开始执行: 更新行情数据")
        logger.info("=" * 60)
        
        start_time = datetime.now()
        
        try:
            # 记录任务开始
            self._log_job_start('update_market_data', '更新行情数据')
            
            # 获取最近的交易日
            today = datetime.now().strftime('%Y-%m-%d')
            
            # 执行增量更新（最近5天）
            result = self.market_data_service.incremental_update(days=5)
            
            # 记录任务完成
            duration = (datetime.now() - start_time).total_seconds()
            
            if result['success']:
                self._log_job_success(
                    'update_market_data',
                    duration,
                    f"更新: {result['updated_count']}条"
                )
                logger.info(f"✓ 行情数据更新成功: 更新{result['updated_count']}条记录")
            else:
                self._log_job_error(
                    'update_market_data',
                    duration,
                    result.get('error', '未知错误')
                )
                logger.error(f"✗ 行情数据更新失败: {result.get('error', '未知错误')}")
                
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            self._log_job_error('update_market_data', duration, str(e))
            logger.error(f"✗ 行情数据更新异常: {e}")
            import traceback
            traceback.print_exc()
        
        logger.info("=" * 60)
    
    def _execute_strategies_job(self):
        """执行策略任务"""
        logger.info("=" * 60)
        logger.info("开始执行: 执行所有启用的策略")
        logger.info("=" * 60)
        
        start_time = datetime.now()
        
        try:
            # 记录任务开始，并保存job_log_id
            job_log_id = self._log_job_start('execute_strategies', '执行策略')
            logger.info(f"任务开始记录: job_log_id={job_log_id}")
            
            # 获取所有启用的策略
            strategies = self.strategy_service.list_strategies(enabled_only=True)
            
            if not strategies:
                logger.info("没有启用的策略需要执行")
                self._log_job_success('execute_strategies', 0, "无启用策略")
                return
            
            logger.info(f"找到 {len(strategies)} 个启用的策略")
            
            # 执行每个策略
            success_count = 0
            error_count = 0
            total_matches = 0
            
            for strategy in strategies:
                strategy_id = strategy['id']
                strategy_name = strategy['name']
                
                logger.info(f"\n执行策略: {strategy_name} (ID: {strategy_id})")
                
                try:
                    # 执行策略（扫描最近30天）
                    # limit_stocks 参数未指定，会根据配置自动应用模式限制
                    result = self.strategy_executor.execute_strategy(
                        strategy_id=strategy_id,
                        start_date=(datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
                        end_date=datetime.now().strftime('%Y-%m-%d')
                    )
                    
                    if result['success']:
                        success_count += 1
                        total_matches += result['matched_count']
                        logger.info(f"  ✓ 策略执行成功: 扫描{result['scanned_stocks']}只, 匹配{result['matched_count']}个")
                        
                        # 记录匹配的股票详情
                        if job_log_id and result.get('matches'):
                            logger.info(f"开始记录{len(result['matches'])}个匹配的股票详情到task_execution_details表")
                            saved_details = 0
                            for match in result['matches']:
                                try:
                                    detail_data = {
                                        'trigger_date': match.get('trigger_date'),
                                        'trigger_pct_change': float(match.get('trigger_pct_change', 0)),
                                        'observation_days': match.get('observation_days'),
                                        'ma_period': match.get('ma_period'),
                                        'observation_result': match.get('observation_result', {})
                                    }
                                    
                                    self.log_task_detail(
                                        job_log_id=job_log_id,
                                        task_type='strategy_execution',
                                        detail_type='strategy_match',
                                        stock_code=match.get('stock_code'),
                                        stock_name=match.get('stock_name'),
                                        detail_data=detail_data
                                    )
                                    saved_details += 1
                                except Exception as e:
                                    logger.error(f"记录股票详情失败: {match.get('stock_code')}, 错误: {e}")
                                    import traceback
                                    traceback.print_exc()
                            logger.info(f"成功记录{saved_details}条股票详情")
                    else:
                        error_count += 1
                        logger.error(f"  ✗ 策略执行失败: {result.get('error', '未知错误')}")
                        
                except Exception as e:
                    error_count += 1
                    logger.error(f"  ✗ 策略执行异常: {e}")
                    import traceback
                    traceback.print_exc()
            
            # 记录任务完成
            duration = (datetime.now() - start_time).total_seconds()
            
            summary = f"成功: {success_count}, 失败: {error_count}, 总匹配: {total_matches}"
            
            if error_count == 0:
                self._log_job_success('execute_strategies', duration, summary)
                logger.info(f"\n✓ 所有策略执行完成: {summary}")
            else:
                self._log_job_error('execute_strategies', duration, summary)
                logger.warning(f"\n⚠ 策略执行完成（有错误）: {summary}")
                
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            self._log_job_error('execute_strategies', duration, str(e))
            logger.error(f"✗ 策略执行任务异常: {e}")
            import traceback
            traceback.print_exc()
        
        logger.info("=" * 60)
    
    def _health_check_job(self):
        """健康检查任务"""
        logger.debug("执行健康检查")
        
        try:
            # 检查数据库连接
            result = self.db.execute_query("SELECT 1")
            
            if result:
                logger.debug("✓ 数据库连接正常")
            else:
                logger.warning("⚠ 数据库连接异常")
                
        except Exception as e:
            logger.error(f"✗ 健康检查失败: {e}")
    
    def _cleanup_zombie_tasks(self):
        """清理僵尸任务（状态为running但实际已停止的任务）"""
        try:
            # 查找所有状态为running的任务
            sql = """
                SELECT id, job_type, job_name, started_at
                FROM job_logs
                WHERE status = 'running'
            """
            
            zombie_tasks = self.db.execute_query(sql)
            
            if not zombie_tasks:
                logger.debug("未发现僵尸任务")
                return
            
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cleaned_count = 0
            
            for task in zombie_tasks:
                task_id = task['id']
                task_name = task['job_name']
                started_at = task['started_at']
                
                # 计算任务运行时长
                try:
                    start_time = datetime.strptime(started_at, '%Y-%m-%d %H:%M:%S')
                    duration = (datetime.now() - start_time).total_seconds()
                except:
                    duration = 0
                
                # 更新任务状态为失败
                update_sql = """
                    UPDATE job_logs
                    SET status = 'failed',
                        completed_at = ?,
                        duration = ?,
                        error = '任务被异常终止（程序重启或崩溃）',
                        message = '任务已终止'
                    WHERE id = ?
                """
                
                self.db.execute_update(
                    update_sql,
                    (now, duration, task_id)
                )
                
                cleaned_count += 1
                logger.info(f"已清理僵尸任务: {task_name} (ID: {task_id}, 运行时长: {duration:.1f}秒)")
            
            if cleaned_count > 0:
                logger.info(f"共清理 {cleaned_count} 个僵尸任务")
                
        except Exception as e:
            logger.error(f"清理僵尸任务失败: {e}")
    
    def _log_job_start(self, job_type: str, job_name: str) -> Optional[int]:
        """
        记录任务开始
        
        Args:
            job_type: 任务类型
            job_name: 任务名称
            
        Returns:
            job_log_id: 任务日志ID
        """
        try:
            sql = """
                INSERT INTO job_logs 
                (job_type, job_name, status, started_at)
                VALUES (?, ?, 'running', ?)
            """
            
            now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            job_log_id = self.db.insert_one('job_logs', {
                'job_type': job_type,
                'job_name': job_name,
                'status': 'running',
                'started_at': now
            })
            return job_log_id
            
        except Exception as e:
            logger.error(f"记录任务开始失败: {e}")
            return None
    
    def _log_job_success(self, job_type: str, duration: float, message: str = ''):
        """
        记录任务成功
        
        Args:
            job_type: 任务类型
            duration: 执行时长（秒）
            message: 消息
        """
        try:
            now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            
            # MySQL不能在UPDATE中直接子查询同一张表，使用JOIN方式
            sql = """
                UPDATE job_logs j
                INNER JOIN (
                    SELECT id 
                    FROM job_logs
                    WHERE job_type = ? AND status = 'running'
                    ORDER BY started_at DESC
                    LIMIT 1
                ) latest ON j.id = latest.id
                SET j.status = 'success',
                    j.completed_at = ?,
                    j.duration = ?,
                    j.message = ?
            """
            self.db.execute_update(sql, (job_type, now, duration, message))
            
        except Exception as e:
            logger.error(f"记录任务成功失败: {e}")
    
    def _log_job_error(self, job_type: str, duration: float, error: str):
        """
        记录任务失败
        
        Args:
            job_type: 任务类型
            duration: 执行时长（秒）
            error: 错误信息
        """
        try:
            now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            
            # MySQL不能在UPDATE中直接子查询同一张表，使用JOIN方式
            sql = """
                UPDATE job_logs j
                INNER JOIN (
                    SELECT id 
                    FROM job_logs
                    WHERE job_type = ? AND status = 'running'
                    ORDER BY started_at DESC
                    LIMIT 1
                ) latest ON j.id = latest.id
                SET j.status = 'error',
                    j.completed_at = ?,
                    j.duration = ?,
                    j.error = ?
            """
            self.db.execute_update(sql, (job_type, now, duration, error))
            
        except Exception as e:
            logger.error(f"记录任务失败失败: {e}")
    
    def log_task_detail(self, job_log_id: int, task_type: str, detail_type: str, 
                       detail_data: Dict[str, Any], stock_code: str = None, 
                       stock_name: str = None):
        """
        记录任务执行详细结果
        
        Args:
            job_log_id: 任务日志ID
            task_type: 任务类型（data_import, strategy_execution等）
            detail_type: 详细类型（stock_import_success, stock_import_failed, strategy_match等）
            detail_data: 详细数据（JSON格式）
            stock_code: 股票代码（可选）
            stock_name: 股票名称（可选）
        """
        try:
            import json
            
            logger.debug(f"记录任务详情: job_log_id={job_log_id}, task_type={task_type}, detail_type={detail_type}, stock_code={stock_code}")
            
            self.db.insert_one('task_execution_details', {
                'job_log_id': job_log_id,
                'task_type': task_type,
                'stock_code': stock_code,
                'stock_name': stock_name,
                'detail_type': detail_type,
                'detail_data': json.dumps(detail_data, ensure_ascii=False)
            })
            
            logger.debug(f"任务详情记录成功: job_log_id={job_log_id}, stock_code={stock_code}")
            
        except Exception as e:
            logger.error(f"记录任务详细结果失败: job_log_id={job_log_id}, stock_code={stock_code}, 错误: {e}")
            import traceback
            traceback.print_exc()
    
    def get_task_details(self, job_log_id: int, limit: int = 1000, 
                        offset: int = 0) -> List[Dict[str, Any]]:
        """
        获取任务执行详细结果
        
        Args:
            job_log_id: 任务日志ID
            limit: 返回记录数
            offset: 偏移量
            
        Returns:
            详细结果列表
        """
        try:
            import json
            
            sql = """
                SELECT *
                FROM task_execution_details
                WHERE job_log_id = ?
                ORDER BY created_at
                LIMIT ? OFFSET ?
            """
            
            details = self.db.execute_query(sql, (job_log_id, limit, offset))
            
            # 解析JSON数据
            for detail in details:
                detail['detail_data'] = json.loads(detail['detail_data'])
            
            return details
            
        except Exception as e:
            logger.error(f"获取任务详细结果失败: {e}")
            return []
    
    def _job_executed_listener(self, event):
        """
        任务执行事件监听器
        
        Args:
            event: 事件对象
        """
        if event.exception:
            logger.error(f"任务执行出错: {event.job_id}, 异常: {event.exception}")
        else:
            logger.debug(f"任务执行完成: {event.job_id}")
    
    def get_job_logs(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        获取任务执行日志
        
        Args:
            limit: 返回记录数
            offset: 偏移量
            
        Returns:
            日志列表
        """
        try:
            sql = """
                SELECT *
                FROM job_logs
                ORDER BY started_at DESC
                LIMIT ? OFFSET ?
            """
            
            logs = self.db.execute_query(sql, (limit, offset))
            return logs
            
        except Exception as e:
            logger.error(f"获取任务日志失败: {e}")
            return []
    
    def get_job_logs_count(self) -> int:
        """
        获取任务日志数量
        
        Returns:
            日志数量
        """
        try:
            result = self.db.execute_query(
                "SELECT COUNT(*) as count FROM job_logs"
            )
            
            if result:
                return result[0]['count']
            
            return 0
            
        except Exception as e:
            logger.error(f"获取任务日志数量失败: {e}")
            return 0
    
    def clear_old_job_logs(self, days: int = 30) -> int:
        """
        清理旧的任务日志
        
        Args:
            days: 保留最近N天的日志
            
        Returns:
            删除的记录数
        """
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            result = self.db.execute_update(
                "DELETE FROM job_logs WHERE started_at < ?",
                (cutoff_date,)
            )
            
            logger.info(f"清理旧日志: 删除{result}条记录")
            return result
            
        except Exception as e:
            logger.error(f"清理旧日志失败: {e}")
            return 0


# 全局任务调度器实例
_task_scheduler = None


def get_task_scheduler() -> TaskScheduler:
    """获取任务调度器实例（单例模式）"""
    global _task_scheduler
    if _task_scheduler is None:
        _task_scheduler = TaskScheduler()
    return _task_scheduler
