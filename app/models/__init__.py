"""数据模型模块初始化"""
from .duckdb_manager import DuckDBManager, get_duckdb
from .orm_models import (
    ORMDatabase, Base,
    Stock, Strategy, StrategyResult,
    SystemLog, DataUpdateHistory,
    JobLog, TaskExecutionDetail
)
from .orm_db import ORMDBAdapter

__all__ = [
    # 原生SQL访问
    'DuckDBManager',
    'get_duckdb',
    
    # ORM模型类
    'ORMDatabase',
    'Base',
    'Stock',
    'Strategy',
    'StrategyResult',
    'SystemLog',
    'DataUpdateHistory',
    'JobLog',
    'TaskExecutionDetail',
    
    # ORM适配器
    'ORMDBAdapter',
]