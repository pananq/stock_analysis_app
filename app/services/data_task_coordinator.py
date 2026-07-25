"""数据导入任务的进程内全局互斥协调器。"""

import threading
import os
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, Optional


class DataTaskBusyError(RuntimeError):
    """已有数据任务占用执行槽。"""

    def __init__(self, active_task: Dict[str, Any]):
        self.active_task = active_task
        super().__init__(
            f"已有数据任务正在执行：{active_task['task_name']}，"
            "请等待该任务完成后再试"
        )


class DataTaskCoordinator:
    """通过数据库原子锁保证跨 Web/API 进程的数据任务串行执行。"""

    LOCK_NAME = 'global_data_import'

    def __init__(self, db=None):
        self._lock = threading.Lock()
        if db is None:
            from app.models.database_factory import get_database

            db = get_database()
        self.db = db
        self._ensure_table()

    def _ensure_table(self):
        self.db.execute_update("""
            CREATE TABLE IF NOT EXISTS data_task_locks (
                lock_name VARCHAR(64) NOT NULL PRIMARY KEY,
                token VARCHAR(64) NOT NULL,
                task_id VARCHAR(64),
                task_type VARCHAR(64) NOT NULL,
                task_name VARCHAR(200) NOT NULL,
                source VARCHAR(32) NOT NULL,
                owner_pid INT NOT NULL,
                acquired_at DATETIME NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

    @staticmethod
    def _pid_alive(pid: int) -> bool:
        try:
            os.kill(int(pid), 0)
            return True
        except (OSError, TypeError, ValueError):
            return False

    def _remove_dead_owner(self, active: Dict[str, Any]) -> bool:
        if self._pid_alive(active.get('owner_pid')):
            return False
        removed = self.db.execute_update(
            "DELETE FROM data_task_locks "
            "WHERE lock_name = %s AND token = %s",
            (self.LOCK_NAME, active['token']),
        )
        return bool(removed)

    def reserve(
        self,
        task_type: str,
        task_name: str,
        source: str,
    ) -> str:
        token = str(uuid.uuid4())
        acquired_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        params = (
            self.LOCK_NAME,
            token,
            task_type,
            task_name,
            source,
            os.getpid(),
            acquired_at,
        )
        with self._lock:
            for attempt in range(2):
                affected = self.db.execute_update(
                    """
                    INSERT IGNORE INTO data_task_locks
                        (lock_name, token, task_type, task_name,
                         source, owner_pid, acquired_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    params,
                )
                if affected:
                    return token
                active = self.current()
                if (
                    attempt == 0
                    and active
                    and self._remove_dead_owner(active)
                ):
                    continue
                if active:
                    raise DataTaskBusyError(active)
                raise RuntimeError("数据任务锁写入失败且未找到占用记录")
        raise RuntimeError("无法预留数据任务执行槽")

    def attach_task_id(self, token: str, task_id: str):
        self.db.execute_update(
            "UPDATE data_task_locks SET task_id = %s "
            "WHERE lock_name = %s AND token = %s",
            (task_id, self.LOCK_NAME, token),
        )

    def release(self, token: str):
        self.db.execute_update(
            "DELETE FROM data_task_locks "
            "WHERE lock_name = %s AND token = %s",
            (self.LOCK_NAME, token),
        )

    def current(self) -> Optional[Dict[str, Any]]:
        rows = self.db.execute_query(
            """
            SELECT token, task_id, task_type, task_name, source,
                   owner_pid, acquired_at AS started_at
            FROM data_task_locks
            WHERE lock_name = %s
            """,
            (self.LOCK_NAME,),
        )
        return dict(rows[0]) if rows else None

    def clear_startup_stale_lock(self):
        """主调度进程启动时清除上一轮服务遗留的执行槽。"""
        active = self.current()
        if active and not self._pid_alive(active.get('owner_pid')):
            self._remove_dead_owner(active)


_coordinator = None
_coordinator_lock = threading.Lock()


def get_data_task_coordinator() -> DataTaskCoordinator:
    global _coordinator
    if _coordinator is None:
        with _coordinator_lock:
            if _coordinator is None:
                _coordinator = DataTaskCoordinator()
    return _coordinator


def create_exclusive_background_task(
    task_manager,
    *,
    task_type: str,
    task_name: str,
    func: Callable,
    kwargs: Optional[Dict[str, Any]] = None,
) -> str:
    """原子预留执行槽并创建后台任务，避免检查与启动之间的竞态。"""
    coordinator = get_data_task_coordinator()
    token = coordinator.reserve(task_type, task_name, source='manual')

    def guarded(**runtime_kwargs):
        try:
            return func(**runtime_kwargs)
        finally:
            coordinator.release(token)

    try:
        task_id = task_manager.create_task(
            task_name=task_name,
            func=guarded,
            kwargs=kwargs or {},
            auto_start=True,
        )
        coordinator.attach_task_id(token, task_id)
        return task_id
    except Exception:
        coordinator.release(token)
        raise
