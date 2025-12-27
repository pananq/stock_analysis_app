"""
MySQL数据库管理模块
负责MySQL数据库的连接、初始化和操作
提供与SQLiteDB相同的API接口
"""
import pymysql
from typing import Optional, List, Dict, Any, ContextManager
from contextlib import contextmanager
from app.utils import get_logger
from dbutils.pooled_db import PooledDB

logger = get_logger(__name__)


class MySQLDB:
    """MySQL数据库管理类"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化数据库连接
        
        Args:
            config: MySQL配置字典，包含host, port, database, username, password等
        """
        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 3306)
        self.database = config.get('database', 'stock_analysis')
        self.username = config.get('username', 'root')
        self.password = config.get('password', '')
        self.charset = config.get('charset', 'utf8mb4')
        self.collation = config.get('collation', 'utf8mb4_unicode_ci')
        
        # 连接池配置
        pool_config = config.get('pool', {})
        self.pool_size = pool_config.get('size', 50)
        self.max_overflow = pool_config.get('max_overflow', 10)
        self.timeout = pool_config.get('timeout', 30)
        self.recycle = pool_config.get('recycle', 3600)
        
        # 初始化连接池
        self._init_pool()
        
        # 初始化数据库表结构
        self._init_database()
    
    def _init_pool(self):
        """初始化数据库连接池"""
        try:
            self.pool = PooledDB(
                creator=pymysql,
                maxconnections=self.pool_size + self.max_overflow,
                mincached=1,
                maxcached=self.pool_size,
                maxusage=None,
                blocking=True,
                maxshared=3,
                host=self.host,
                port=self.port,
                user=self.username,
                password=self.password,
                database=self.database,
                charset=self.charset,
                cursorclass=pymysql.cursors.DictCursor,
                connect_timeout=self.timeout,
                read_timeout=self.timeout,
                write_timeout=self.timeout
            )
            logger.info(f"MySQL连接池初始化成功: {self.host}:{self.port}/{self.database}")
        except Exception as e:
            logger.error(f"MySQL连接池初始化失败: {e}")
            raise
    
    @contextmanager
    def get_connection(self) -> ContextManager:
        """
        获取数据库连接的上下文管理器
        
        Yields:
            pymysql.Connection: 数据库连接对象
        """
        conn = None
        try:
            conn = self.pool.connection()
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"数据库操作失败: {e}", exc_info=True)
            raise
        finally:
            if conn:
                conn.close()
    
    def _init_database(self):
        """初始化数据库表结构"""
        logger.info("初始化MySQL数据库...")
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 创建stocks表（股票基础信息）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stocks (
                    code VARCHAR(20) PRIMARY KEY,
                    name VARCHAR(500) NOT NULL,
                    list_date DATE,
                    industry VARCHAR(200),
                    market_type VARCHAR(50),
                    status VARCHAR(50) DEFAULT 'normal',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_status (status),
                    INDEX idx_industry (industry),
                    INDEX idx_market_type (market_type)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            ''')
            
            # 创建strategies表（策略配置）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS strategies (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(500) NOT NULL UNIQUE,
                    description TEXT,
                    config TEXT NOT NULL,
                    enabled TINYINT(1) DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    last_executed_at DATETIME,
                    INDEX idx_enabled (enabled)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            ''')
            
            # 创建strategy_results表（策略执行结果）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS strategy_results (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    strategy_id INT NOT NULL,
                    stock_code VARCHAR(20) NOT NULL,
                    stock_name VARCHAR(100),
                    trigger_date DATE NOT NULL,
                    trigger_price DECIMAL(10,4),
                    trigger_pct_change DECIMAL(10,2),
                    observation_days INT,
                    ma_period INT,
                    observation_result TEXT,
                    result_data TEXT,
                    executed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (strategy_id) REFERENCES strategies(id) ON DELETE CASCADE,
                    FOREIGN KEY (stock_code) REFERENCES stocks(code) ON DELETE CASCADE,
                    INDEX idx_strategy_id (strategy_id),
                    INDEX idx_stock_code (stock_code),
                    INDEX idx_trigger_date (trigger_date),
                    INDEX idx_executed_at (executed_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            ''')
            
            # 创建system_logs表（系统日志）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    level VARCHAR(50) NOT NULL,
                    module VARCHAR(200) NOT NULL,
                    message TEXT NOT NULL,
                    details TEXT,
                    INDEX idx_timestamp (timestamp),
                    INDEX idx_level (level),
                    INDEX idx_module (module)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            ''')
            
            # 创建data_update_history表（数据更新历史）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS data_update_history (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    update_type VARCHAR(100) NOT NULL,
                    start_time DATETIME NOT NULL,
                    end_time DATETIME,
                    total_count INT DEFAULT 0,
                    success_count INT DEFAULT 0,
                    fail_count INT DEFAULT 0,
                    status VARCHAR(50) DEFAULT 'running',
                    error_message TEXT,
                    INDEX idx_update_type (update_type),
                    INDEX idx_status (status),
                    INDEX idx_start_time (start_time)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            ''')
            
            # 创建job_logs表（定时任务执行日志）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS job_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    job_type VARCHAR(100) NOT NULL,
                    job_name VARCHAR(200) NOT NULL,
                    status VARCHAR(50) NOT NULL,
                    started_at DATETIME NOT NULL,
                    completed_at DATETIME,
                    duration DECIMAL(10,4),
                    message TEXT,
                    error TEXT,
                    INDEX idx_job_type (job_type),
                    INDEX idx_status (status),
                    INDEX idx_started_at (started_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            ''')
            
            # 创建task_execution_details表（任务执行详细结果）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_execution_details (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    job_log_id INT NOT NULL,
                    task_type VARCHAR(100) NOT NULL,
                    stock_code VARCHAR(20),
                    stock_name VARCHAR(500),
                    detail_type VARCHAR(100) NOT NULL,
                    detail_data TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (job_log_id) REFERENCES job_logs(id) ON DELETE CASCADE,
                    INDEX idx_job_log_id (job_log_id),
                    INDEX idx_task_type (task_type),
                    INDEX idx_stock_code (stock_code),
                    INDEX idx_detail_type (detail_type)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            ''')
            
            logger.info("MySQL数据库初始化完成")
    
    def execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """
        执行查询语句
        
        Args:
            query: SQL查询语句
            params: 查询参数
            
        Returns:
            查询结果列表（字典列表）
        """
        import time
        start_time = time.time()
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(pymysql.cursors.DictCursor)  # 使用字典游标
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                results = cursor.fetchall()
                
                # 记录操作日志
                execution_time = time.time() - start_time
                self._log_operation(query, params, execution_time, len(results))
                
                # 慢查询警告
                if execution_time > 0.1:  # 超过100ms
                    logger.warning(f"慢查询检测 (耗时{execution_time:.3f}s): {query[:100]}...")
                
                return results
        except Exception as e:
            logger.error(f"查询执行失败: {query[:100]}... 错误: {e}", exc_info=True)
            raise
    
    def execute_update(self, query: str, params: tuple = None) -> int:
        """
        执行更新语句（INSERT, UPDATE, DELETE）
        
        Args:
            query: SQL更新语句
            params: 更新参数
            
        Returns:
            影响的行数
        """
        import time
        start_time = time.time()
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                affected_rows = cursor.rowcount
                
                # 记录操作日志
                execution_time = time.time() - start_time
                self._log_operation(query, params, execution_time, affected_rows)
                
                return affected_rows
        except Exception as e:
            logger.error(f"更新执行失败: {query[:100]}... 错误: {e}", exc_info=True)
            raise
    
    def execute_many(self, query: str, params_list: List[tuple]) -> int:
        """
        批量执行更新语句
        
        Args:
            query: SQL更新语句
            params_list: 参数列表
            
        Returns:
            影响的行数
        """
        import time
        start_time = time.time()
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.executemany(query, params_list)
                affected_rows = cursor.rowcount
                
                # 记录操作日志
                execution_time = time.time() - start_time
                logger.debug(f"批量操作: 影响行数={affected_rows}, 耗时={execution_time:.3f}s")
                
                return affected_rows
        except Exception as e:
            logger.error(f"批量操作失败: {query[:100]}... 错误: {e}", exc_info=True)
            raise
    
    def insert_one(self, table: str, data: Dict[str, Any]) -> int:
        """
        插入单条记录
        
        Args:
            table: 表名
            data: 数据字典
            
        Returns:
            插入记录的ID
        """
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['%s' for _ in data])
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(data.values()))
            return cursor.lastrowid
    
    def update_one(self, table: str, data: Dict[str, Any], where: Dict[str, Any]) -> int:
        """
        更新单条记录
        
        Args:
            table: 表名
            data: 要更新的数据字典
            where: 条件字典
            
        Returns:
            影响的行数
        """
        set_clause = ', '.join([f"{k} = %s" for k in data.keys()])
        where_clause = ' AND '.join([f"{k} = %s" for k in where.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
        
        params = tuple(data.values()) + tuple(where.values())
        return self.execute_update(query, params)
    
    def delete(self, table: str, where: Dict[str, Any]) -> int:
        """
        删除记录
        
        Args:
            table: 表名
            where: 条件字典
            
        Returns:
            影响的行数
        """
        where_clause = ' AND '.join([f"{k} = %s" for k in where.keys()])
        query = f"DELETE FROM {table} WHERE {where_clause}"
        
        return self.execute_update(query, tuple(where.values()))
    
    def _log_operation(self, query: str, params: tuple, execution_time: float, affected_rows: int):
        """
        记录数据库操作日志
        
        Args:
            query: SQL语句
            params: 参数
            execution_time: 执行时间
            affected_rows: 影响行数
        """
        logger.debug(
            f"SQL操作 - 耗时:{execution_time:.4f}s, 影响行数:{affected_rows}, "
            f"SQL:{query[:100]}{'...' if len(query) > 100 else ''}"
        )
    
    def get_connection_pool_size(self) -> int:
        """获取当前连接池大小"""
        return self.pool._maxconnections
    
    def close_all_connections(self):
        """关闭所有连接"""
        # PooledDB会自动管理连接池，这里主要用于清理
        logger.info("MySQL连接池已清理")


# 全局数据库实例
_db_instance: Optional[MySQLDB] = None


def get_mysql_db(config: Dict[str, Any] = None) -> MySQLDB:
    """
    获取全局MySQL数据库实例
    
    Args:
        config: MySQL配置字典
        
    Returns:
        MySQLDB实例
    """
    global _db_instance
    if _db_instance is None:
        if config is None:
            from app.utils import get_config
            config_manager = get_config()
            config = config_manager.get('database.mysql')
        _db_instance = MySQLDB(config)
    return _db_instance
