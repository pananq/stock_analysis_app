"""
ORM 数据库适配器
使用 SQLAlchemy ORM 提供 MySQL 和 SQLite 的统一访问接口
"""
from typing import Dict, Any
from app.models.orm_models import ORMDatabase
from app.utils import get_logger

logger = get_logger(__name__)


class ORMDBAdapter:
    """
    ORM数据库适配器类
    使用SQLAlchemy ORM提供统一的数据库操作接口
    兼容现有的数据库接口（execute_query, execute_update, insert_one等）
    """
    
    def __init__(self, db_type: str, config: Dict[str, Any]):
        """
        初始化ORM数据库适配器
        
        Args:
            db_type: 数据库类型（mysql或sqlite）
            config: 数据库配置
        """
        self.db_type = db_type
        self.config = config
        self.orm_db = None
        self._init_database()
    
    def _init_database(self):
        """初始化ORM数据库"""
        db_url = self._build_db_url()
        logger.info(f"初始化ORM数据库: {self.db_type}")
        self.orm_db = ORMDatabase(db_url)
        logger.info(f"ORM数据库初始化成功: {self.db_type}")
    
    def _build_db_url(self) -> str:
        """
        构建数据库连接URL
        
        Returns:
            数据库连接URL字符串
        """
        if self.db_type == 'mysql':
            # MySQL连接URL: mysql+pymysql://user:password@host:port/database
            host = self.config.get('host', 'localhost')
            port = self.config.get('port', 3306)
            database = self.config.get('database', 'stock_analysis')
            username = self.config.get('username', 'root')
            password = self.config.get('password', '')
            charset = self.config.get('charset', 'utf8mb4')
            
            return f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}?charset={charset}"
        
        else:
            raise ValueError(f"不支持的数据库类型: {self.db_type}，只支持mysql")
    
    def execute_query(self, query: str, params: tuple = None) -> list:
        """
        执行查询语句
        
        Args:
            query: SQL查询语句
            params: 查询参数
            
        Returns:
            查询结果列表
        """
        # 将SQLite风格的占位符转换为SQLAlchemy支持的格式
        # SQLAlchemy在MySQL上会自动处理参数占位符
        return self.orm_db.execute_query(query, params)
    
    def execute_update(self, query: str, params: tuple = None) -> int:
        """
        执行更新语句（INSERT, UPDATE, DELETE）
        
        Args:
            query: SQL更新语句
            params: 更新参数
            
        Returns:
            影响的行数
        """
        return self.orm_db.execute_update(query, params)
    
    def execute_many(self, query: str, params_list: list) -> int:
        """
        批量执行更新语句
        
        Args:
            query: SQL更新语句
            params_list: 参数列表
            
        Returns:
            影响的行数
        """
        return self.orm_db.execute_many(query, params_list)
    
    def insert_one(self, table: str, data: Dict[str, Any]) -> int:
        """
        插入单条记录
        
        Args:
            table: 表名
            data: 数据字典
            
        Returns:
            插入记录的ID
        """
        return self.orm_db.insert_one(table, data)
    
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
        return self.orm_db.update_one(table, data, where)
    
    def delete(self, table: str, where: Dict[str, Any]) -> int:
        """
        删除记录
        
        Args:
            table: 表名
            where: 条件字典
            
        Returns:
            影响的行数
        """
        return self.orm_db.delete(table, where)
    
    def get_session(self):
        """
        获取SQLAlchemy会话对象
        用于需要直接使用ORM功能的场景
        
        Returns:
            Session: SQLAlchemy会话对象
        """
        return self.orm_db.get_session()
    
    def close(self):
        """关闭数据库连接"""
        if self.orm_db:
            self.orm_db.close()
