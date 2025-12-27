"""
DuckDB数据库管理模块
负责DuckDB数据库的连接、初始化和操作（用于存储历史行情数据）
"""
import duckdb
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
import threading
from app.utils import get_logger

logger = get_logger(__name__)


class DuckDBManager:
    """DuckDB数据库管理类"""
    
    def __init__(self, db_path: str):
        """
        初始化数据库连接
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._db_lock = threading.Lock()  # 全局数据库锁，防止并发访问
        self._ensure_db_directory()
        self._init_database()
    
    def _ensure_db_directory(self):
        """确保数据库目录存在"""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
    
    @contextmanager
    def get_connection(self):
        """
        获取数据库连接的上下文管理器
        
        Yields:
            DuckDB连接对象
        """
        # 使用锁确保同一时间只有一个线程访问数据库
        with self._db_lock:
            # 禁用DuckDB文件锁以支持多进程并发访问
            # 设置max_memory和threads参数
            conn = duckdb.connect(
                self.db_path,
                read_only=False,
                config={
                    'enable_external_access': False,  # 禁用外部访问
                    'max_memory': '2GB',  # 限制内存使用
                    'threads': 4,  # 限制线程数
                }
            )
            try:
                yield conn
            except Exception as e:
                logger.error(f"数据库操作失败: {e}")
                raise
            finally:
                conn.close()
    
    def _init_database(self):
        """初始化数据库表结构"""
        logger.info("初始化DuckDB数据库...")
        
        with self.get_connection() as conn:
            # 创建daily_market表（股票日线行情数据）
            conn.execute('''
                CREATE TABLE IF NOT EXISTS daily_market (
                    code VARCHAR NOT NULL,
                    trade_date DATE NOT NULL,
                    open DECIMAL(10, 2),
                    close DECIMAL(10, 2),
                    high DECIMAL(10, 2),
                    low DECIMAL(10, 2),
                    volume BIGINT,
                    amount DECIMAL(20, 2),
                    change_pct DECIMAL(10, 2),
                    turnover_rate DECIMAL(10, 2),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (code, trade_date)
                )
            ''')
            
            # 创建索引以优化查询性能
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_daily_market_code 
                ON daily_market(code)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_daily_market_date 
                ON daily_market(trade_date)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_daily_market_code_date 
                ON daily_market(code, trade_date)
            ''')
            
            logger.info("DuckDB数据库初始化完成")
    
    def execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """
        执行查询语句
        
        Args:
            query: SQL查询语句
            params: 查询参数
            
        Returns:
            查询结果列表
        """
        with self.get_connection() as conn:
            if params:
                result = conn.execute(query, params).fetchall()
            else:
                result = conn.execute(query).fetchall()
            
            # 获取列名
            columns = [desc[0] for desc in conn.description]
            
            # 将结果转换为字典列表
            return [dict(zip(columns, row)) for row in result]
    
    def execute_update(self, query: str, params: tuple = None) -> int:
        """
        执行更新语句（INSERT, UPDATE, DELETE）
        
        Args:
            query: SQL更新语句
            params: 更新参数
            
        Returns:
            影响的行数
        """
        with self.get_connection() as conn:
            if params:
                conn.execute(query, params)
            else:
                conn.execute(query)
            # DuckDB不直接返回rowcount，需要通过其他方式获取
            return 1
    
    def insert_many(self, table: str, data_list: List[Dict[str, Any]]) -> int:
        """
        批量插入数据
        
        Args:
            table: 表名
            data_list: 数据字典列表
            
        Returns:
            插入的行数
        """
        if not data_list:
            return 0
        
        # 获取列名
        columns = list(data_list[0].keys())
        columns_str = ', '.join(columns)
        placeholders = ', '.join(['?' for _ in columns])
        
        # 使用ON CONFLICT DO NOTHING来忽略重复数据
        query = f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
        
        with self.get_connection() as conn:
            # 准备数据
            values_list = [tuple(d[col] for col in columns) for d in data_list]
            conn.executemany(query, values_list)
            return len(data_list)
    
    def insert_dataframe(self, table: str, df) -> int:
        """
        从DataFrame批量插入数据
        
        Args:
            table: 表名
            df: pandas DataFrame
            
        Returns:
            插入的行数
        """
        if df.empty:
            return 0
        
        # 将DataFrame转换为字典列表
        data_list = df.to_dict('records')
        return self.insert_many(table, data_list)
    
    def get_stock_history(self, stock_code: str, start_date: str = None, 
                         end_date: str = None, limit: int = None) -> List[Dict[str, Any]]:
        """
        获取股票历史行情数据
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期（YYYY-MM-DD）
            end_date: 结束日期（YYYY-MM-DD）
            limit: 限制返回记录数
            
        Returns:
            行情数据列表
        """
        query = "SELECT * FROM stock_daily WHERE stock_code = ?"
        params = [stock_code]
        
        if start_date:
            query += " AND trade_date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND trade_date <= ?"
            params.append(end_date)
        
        query += " ORDER BY trade_date DESC"
        
        if limit:
            query += f" LIMIT {limit}"
        
        return self.execute_query(query, tuple(params))
    
    def get_latest_date(self, stock_code: str = None) -> Optional[str]:
        """
        获取最新的交易日期
        
        Args:
            stock_code: 股票代码，如果为None则获取所有股票的最新日期
            
        Returns:
            最新交易日期（YYYY-MM-DD格式）
        """
        if stock_code:
            query = "SELECT MAX(trade_date) as max_date FROM stock_daily WHERE stock_code = ?"
            params = (stock_code,)
        else:
            query = "SELECT MAX(trade_date) as max_date FROM stock_daily"
            params = None
        
        result = self.execute_query(query, params)
        if result and result[0]['max_date']:
            return str(result[0]['max_date'])
        return None
    
    def get_stock_count(self) -> int:
        """
        获取数据库中的股票数量
        
        Returns:
            股票数量
        """
        query = "SELECT COUNT(DISTINCT stock_code) as count FROM stock_daily"
        result = self.execute_query(query)
        return result[0]['count'] if result else 0
    
    def delete_stock_data(self, stock_code: str) -> int:
        """
        删除指定股票的所有数据
        
        Args:
            stock_code: 股票代码
            
        Returns:
            删除的行数
        """
        query = "DELETE FROM stock_daily WHERE stock_code = ?"
        return self.execute_update(query, (stock_code,))
    
    def calculate_ma(self, stock_code: str, period: int, end_date: str = None) -> List[Dict[str, Any]]:
        """
        计算移动平均线
        
        Args:
            stock_code: 股票代码
            period: 均线周期
            end_date: 结束日期
            
        Returns:
            包含MA值的数据列表
        """
        query = f'''
            SELECT 
                stock_code,
                trade_date,
                close_price,
                AVG(close_price) OVER (
                    PARTITION BY stock_code 
                    ORDER BY trade_date 
                    ROWS BETWEEN {period-1} PRECEDING AND CURRENT ROW
                ) as ma_{period}
            FROM stock_daily
            WHERE stock_code = ?
        '''
        
        params = [stock_code]
        
        if end_date:
            query += " AND trade_date <= ?"
            params.append(end_date)
        
        query += " ORDER BY trade_date DESC"
        
        return self.execute_query(query, tuple(params))


# 全局数据库实例
_duckdb_instance: Optional[DuckDBManager] = None


def get_duckdb(db_path: str = None) -> DuckDBManager:
    """
    获取全局DuckDB数据库实例
    
    Args:
        db_path: 数据库文件路径
        
    Returns:
        DuckDBManager实例
    """
    global _duckdb_instance
    if _duckdb_instance is None:
        if db_path is None:
            from app.utils import get_config
            config = get_config()
            db_path = config.get('database.duckdb_path')
        _duckdb_instance = DuckDBManager(db_path)
    return _duckdb_instance
