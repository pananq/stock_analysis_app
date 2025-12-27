"""
数据库适配器工厂模块
提供统一的数据库访问接口，支持MySQL数据库
"""
from typing import Union
from abc import ABC, abstractmethod
from app.utils import get_logger, get_config
from app.models.mysql_db import MySQLDB, get_mysql_db
from app.models.orm_db import ORMDBAdapter

logger = get_logger(__name__)


class DatabaseAdapter(ABC):
    """数据库适配器抽象基类，定义统一的数据库操作接口"""
    
    @abstractmethod
    def execute_query(self, query: str, params: tuple = None) -> list:
        """执行查询语句"""
        pass
    
    @abstractmethod
    def execute_update(self, query: str, params: tuple = None) -> int:
        """执行更新语句"""
        pass
    
    @abstractmethod
    def execute_many(self, query: str, params_list: list) -> int:
        """批量执行更新语句"""
        pass
    
    @abstractmethod
    def insert_one(self, table: str, data: dict) -> int:
        """插入单条记录"""
        pass
    
    @abstractmethod
    def update_one(self, table: str, data: dict, where: dict) -> int:
        """更新单条记录"""
        pass
    
    @abstractmethod
    def delete(self, table: str, where: dict) -> int:
        """删除记录"""
        pass


class DatabaseFactory:
    """数据库适配器工厂类"""
    
    _instance = None
    _db_adapter = None
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super(DatabaseFactory, cls).__new__(cls)
        return cls._instance
    
    def get_database(self, db_type: str = None, config: dict = None, use_orm: bool = True) -> Union[MySQLDB, ORMDBAdapter]:
        """
        获取数据库适配器实例
        
        Args:
            db_type: 数据库类型（仅支持mysql），如果为None则从配置读取
            config: 数据库配置字典，如果为None则从配置读取
            use_orm: 是否使用ORM模式（默认True）
            
        Returns:
            数据库适配器实例（MySQLDB或ORMDBAdapter）
        """
        # 如果已经初始化过，直接返回缓存的实例
        if self._db_adapter is not None:
            return self._db_adapter
        
        # 如果没有指定数据库类型，从配置读取
        if db_type is None:
            config_manager = get_config()
            db_type = config_manager.get('database.type', 'mysql')
        
        # 优先使用ORM模式
        if use_orm and db_type.lower() == 'mysql':
            logger.info(f"初始化ORM数据库适配器: 类型={db_type}")
            
            if config is None:
                config_manager = get_config()
                mysql_config = config_manager.get('database.mysql')
                self._db_adapter = ORMDBAdapter('mysql', mysql_config)
            else:
                self._db_adapter = ORMDBAdapter('mysql', config)
            
            logger.info(f"ORM数据库适配器初始化成功: {db_type}")
            return self._db_adapter
        
        # 不使用ORM模式，使用原生SQL模式
        logger.info(f"初始化原生SQL数据库适配器: 类型={db_type}")
        
        if db_type.lower() == 'mysql':
            if config is None:
                config_manager = get_config()
                mysql_config = config_manager.get('database.mysql')
                self._db_adapter = get_mysql_db(mysql_config)
            else:
                self._db_adapter = MySQLDB(config)
        
        else:
            raise ValueError(f"不支持的数据库类型: {db_type}，只支持mysql")
        
        logger.info(f"数据库适配器初始化成功: {db_type}")
        return self._db_adapter
    
    def reset(self):
        """重置数据库实例（主要用于测试或切换数据库）"""
        if self._db_adapter is not None:
            logger.info("重置数据库适配器")
            self._db_adapter = None
    
    def get_current_type(self) -> str:
        """获取当前使用的数据库类型"""
        config_manager = get_config()
        return config_manager.get('database.type', 'mysql')


# 全局工厂实例
_db_factory = None


def get_database(db_type: str = None, config: dict = None, use_orm: bool = True) -> Union[MySQLDB, ORMDBAdapter]:
    """
    获取数据库实例的便捷函数
    
    Args:
        db_type: 数据库类型（仅支持mysql），如果为None则从配置读取
        config: 数据库配置字典，如果为None则从配置读取
        use_orm: 是否使用ORM模式（默认True）
        
    Returns:
        数据库实例（MySQLDB或ORMDBAdapter）
        
    使用示例:
        # 使用配置文件中的数据库类型（默认使用ORM）
        db = get_database()
        
        # 指定使用MySQL
        db = get_database('mysql')
        
        # 不使用ORM模式（使用原生SQL）
        db = get_database(use_orm=False)
    """
    global _db_factory
    if _db_factory is None:
        _db_factory = DatabaseFactory()
    return _db_factory.get_database(db_type, config, use_orm)


def switch_database(db_type: str, config: dict = None):
    """
    切换数据库类型
    
    Args:
        db_type: 目标数据库类型（仅支持mysql）
        config: 数据库配置字典（可选）
        
    注意:
        目前只支持MySQL数据库
    """
    global _db_factory
    if _db_factory is None:
        _db_factory = DatabaseFactory()
    
    logger.info(f"切换数据库类型到: {db_type}")
    _db_factory.reset()
    
    # 更新配置文件中的数据库类型
    config_manager = get_config()
    config_manager.set('database.type', db_type.lower())
    config_manager.save()
    
    # 初始化新数据库
    _db_factory.get_database(db_type, config)
    logger.info(f"数据库切换完成: {db_type}")
