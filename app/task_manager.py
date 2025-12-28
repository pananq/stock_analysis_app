"""
后台任务管理模块

支持长时间运行的后台任务，并提供进度查询功能
"""

import threading
import uuid
from typing import Dict, Any, Callable, Optional
from datetime import datetime
from app.utils import get_logger

logger = get_logger(__name__)


class BackgroundTask:
    """后台任务类"""
    
    def __init__(self, task_id: str, task_name: str, func: Callable, 
                 args: tuple = (), kwargs: Dict = None):
        """
        初始化后台任务
        
        Args:
            task_id: 任务ID
            task_name: 任务名称
            func: 任务执行函数
            args: 位置参数
            kwargs: 关键字参数
        """
        self.task_id = task_id
        self.task_name = task_name
        self.func = func
        self.args = args
        self.kwargs = kwargs or {}
        
        # 任务状态
        self.status = 'pending'  # pending, running, completed, failed
        self.progress = 0.0  # 进度百分比 0-100
        self.message = '等待开始'
        
        # 任务时间
        from datetime import datetime
        self.created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.started_at = None
        self.completed_at = None
        
        # 任务结果
        self.result = None
        self.error = None
        
        # 线程
        self.thread = None
        self._stop_event = threading.Event()
        
    def _run_with_progress(self):
        """运行任务并支持进度更新"""
        from datetime import datetime
        try:
            self.status = 'running'
            self.started_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.message = '正在执行...'
            self._update()

            # 传递进度回调函数和停止事件
            if 'progress_callback' not in self.kwargs:
                self.kwargs['progress_callback'] = self.update_progress

            # 传递stop_event到执行函数
            self.kwargs['stop_event'] = self._stop_event

            # 执行任务
            self.result = self.func(*self.args, **self.kwargs)

            # 检查是否被取消
            if self.is_stopped():
                self.status = 'failed'
                self.completed_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self.error = '任务已取消'
                self.message = '任务已被取消'
                logger.warning(f"任务 {self.task_id} ({self.task_name}) 已取消")
            else:
                # 任务完成
                self.status = 'completed'
                self.completed_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self.progress = 100.0
                self.message = '任务完成'
                logger.info(f"任务 {self.task_id} ({self.task_name}) 完成")

        except Exception as e:
            self.status = 'failed'
            self.completed_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.error = str(e)
            self.message = f'任务失败: {e}'
            logger.error(f"任务 {self.task_id} ({self.task_name}) 失败: {e}")

        finally:
            self._update()
    
    def start(self):
        """启动任务"""
        if self.thread is None:
            self.thread = threading.Thread(
                target=self._run_with_progress,
                name=f"Task-{self.task_id}",
                daemon=False
            )
            self.thread.start()
            logger.info(f"任务 {self.task_id} ({self.task_name}) 已启动")
    
    def wait(self, timeout: Optional[float] = None):
        """等待任务完成"""
        if self.thread:
            self.thread.join(timeout=timeout)
    
    def stop(self):
        """停止任务"""
        self._stop_event.set()
        if self.thread and self.thread.is_alive():
            logger.warning(f"尝试停止任务 {self.task_id}")
            # 注意：Python线程不能强制停止，只能通过_stop_event检查
    
    def is_stopped(self):
        """检查是否被请求停止"""
        return self._stop_event.is_set()
    
    def update_progress(self, progress: float, message: str = None):
        """
        更新任务进度
        
        Args:
            progress: 进度百分比 0-100
            message: 进度消息
        """
        self.progress = min(100.0, max(0.0, progress))
        if message:
            self.message = message
        self._update()
        logger.debug(f"任务 {self.task_id} 进度: {self.progress:.1f}% - {self.message}")
    
    def _update(self):
        """更新任务状态到管理器"""
        get_task_manager().update_task_status(self.task_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'task_id': self.task_id,
            'task_name': self.task_name,
            'status': self.status,
            'progress': self.progress,
            'message': self.message,
            'created_at': self.created_at,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'error': self.error,
            'is_running': self.thread and self.thread.is_alive() if self.thread else False,
            'result': self.result
        }


class BackgroundTaskManager:
    """后台任务管理器"""
    
    def __init__(self):
        """初始化任务管理器"""
        self.tasks: Dict[str, BackgroundTask] = {}
        self._lock = threading.Lock()
        logger.info("后台任务管理器初始化完成")
    
    def create_task(self, task_name: str, func: Callable, 
                   args: tuple = (), kwargs: Dict = None,
                   auto_start: bool = True) -> str:
        """
        创建后台任务
        
        Args:
            task_name: 任务名称
            func: 任务函数
            args: 位置参数
            kwargs: 关键字参数
            auto_start: 是否自动启动
            
        Returns:
            任务ID
        """
        task_id = str(uuid.uuid4())
        
        task = BackgroundTask(task_id, task_name, func, args, kwargs)
        
        with self._lock:
            self.tasks[task_id] = task
        
        if auto_start:
            task.start()
        
        logger.info(f"创建任务 {task_id} ({task_name})")
        return task_id
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务信息字典
        """
        with self._lock:
            task = self.tasks.get(task_id)
            return task.to_dict() if task else None
    
    def update_task_status(self, task_id: str):
        """更新任务状态（内部使用）"""
        # 可以在这里添加持久化逻辑
        pass
    
    def list_tasks(self, status: str = None) -> list:
        """
        获取任务列表
        
        Args:
            status: 状态过滤（可选）
            
        Returns:
            任务列表
        """
        with self._lock:
            tasks = list(self.tasks.values())
            if status:
                tasks = [t for t in tasks if t.status == status]
            return [t.to_dict() for t in tasks]
    
    def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否成功
        """
        with self._lock:
            task = self.tasks.get(task_id)
            if task and task.status in ['pending', 'running']:
                task.stop()
                logger.info(f"任务 {task_id} 已请求取消")
                return True
        return False
    
    def cleanup_completed_tasks(self, keep_hours: int = 24):
        """
        清理已完成的任务

        Args:
            keep_hours: 保留最近几小时的任务
        """
        from datetime import datetime

        with self._lock:
            current_time = datetime.now()
            to_remove = []

            for task_id, task in self.tasks.items():
                if task.status in ['completed', 'failed']:
                    if task.completed_at:
                        try:
                            # 直接使用datetime对象比较，无需时区转换
                            completed_time = datetime.strptime(
                                task.completed_at,
                                '%Y-%m-%d %H:%M:%S'
                            )
                        except:
                            continue

                        hours_elapsed = (current_time - completed_time).total_seconds() / 3600
                        if hours_elapsed > keep_hours:
                            to_remove.append(task_id)
            
            for task_id in to_remove:
                del self.tasks[task_id]
            
            if to_remove:
                logger.info(f"清理了 {len(to_remove)} 个已完成任务")


# 全局任务管理器实例
_task_manager_instance: Optional[BackgroundTaskManager] = None


def get_task_manager() -> BackgroundTaskManager:
    """
    获取全局任务管理器实例
    
    Returns:
        BackgroundTaskManager实例
    """
    global _task_manager_instance
    if _task_manager_instance is None:
        _task_manager_instance = BackgroundTaskManager()
    return _task_manager_instance
