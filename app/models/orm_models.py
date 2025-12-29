"""
SQLAlchemy ORM 模型定义
用于 MySQL 和 SQLite 数据库的 ORM 操作
"""
import re
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, DateTime, 
    Date, Boolean, Float, Index, Numeric, BigInteger
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from app.utils import get_logger

logger = get_logger(__name__)

# 声明基类
Base = declarative_base()


class Stock(Base):
    """股票基础信息表"""
    __tablename__ = 'stocks'
    
    code = Column(String(20), primary_key=True, comment='股票代码')
    name = Column(String(500), nullable=False, comment='股票名称')
    list_date = Column(Date, comment='上市日期')
    industry = Column(String(200), comment='所属行业')
    market_type = Column(String(50), comment='市场类型')
    status = Column(String(50), default='normal', comment='状态')
    earliest_data_date = Column(Date, comment='最早数据日期')
    latest_data_date = Column(Date, comment='最近数据日期')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    
    # 索引
    __table_args__ = (
        Index('idx_status', 'status'),
        Index('idx_industry', 'industry'),
        Index('idx_market_type', 'market_type'),
        Index('idx_earliest_data_date', 'earliest_data_date'),
        Index('idx_latest_data_date', 'latest_data_date'),
    )


class User(Base):
    """用户表"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment='用户ID')
    username = Column(String(50), nullable=False, unique=True, comment='用户名')
    password_hash = Column(String(255), nullable=False, comment='密码哈希')
    role = Column(String(20), nullable=False, default='user', comment='角色(admin/user)')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    last_login = Column(DateTime, comment='最后登录时间')
    
    # 索引
    __table_args__ = (
        Index('idx_username', 'username'),
        Index('idx_role', 'role'),
    )


class Strategy(Base):
    """策略配置表"""
    __tablename__ = 'strategies'
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment='策略ID')
    user_id = Column(Integer, comment='所属用户ID')
    name = Column(String(500), nullable=False, unique=True, comment='策略名称')
    description = Column(Text, comment='策略描述')
    config = Column(Text, nullable=False, comment='策略配置（JSON格式）')
    enabled = Column(Boolean, default=True, comment='是否启用')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    last_executed_at = Column(DateTime, comment='最后执行时间')
    
    # 索引
    __table_args__ = (
        Index('idx_enabled', 'enabled'),
        Index('idx_strategies_user_id', 'user_id'),
    )


class StrategyResult(Base):
    """策略执行结果表"""
    __tablename__ = 'strategy_results'
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment='结果ID')
    strategy_id = Column(Integer, nullable=False, comment='策略ID')
    stock_code = Column(String(20), nullable=False, comment='股票代码')
    trigger_date = Column(Date, nullable=False, comment='触发日期')
    trigger_price = Column(Float(10, 4), comment='触发价格')
    rise_percent = Column(Float(10, 4), comment='涨幅')
    result_data = Column(Text, comment='结果数据（JSON格式）')
    executed_at = Column(DateTime, default=datetime.now, comment='执行时间')
    
    # 索引
    __table_args__ = (
        Index('idx_strategy_id', 'strategy_id'),
        Index('idx_stock_code', 'stock_code'),
        Index('idx_trigger_date', 'trigger_date'),
        Index('idx_executed_at', 'executed_at'),
    )


class SystemLog(Base):
    """系统日志表"""
    __tablename__ = 'system_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment='日志ID')
    timestamp = Column(DateTime, default=datetime.now, comment='时间戳')
    level = Column(String(50), nullable=False, comment='日志级别')
    module = Column(String(200), nullable=False, comment='模块名称')
    message = Column(Text, nullable=False, comment='日志消息')
    details = Column(Text, comment='详细信息')
    
    # 索引
    __table_args__ = (
        Index('idx_timestamp', 'timestamp'),
        Index('idx_level', 'level'),
        Index('idx_module', 'module'),
    )


class DataUpdateHistory(Base):
    """数据更新历史表"""
    __tablename__ = 'data_update_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment='记录ID')
    update_type = Column(String(100), nullable=False, comment='更新类型')
    start_time = Column(DateTime, nullable=False, comment='开始时间')
    end_time = Column(DateTime, comment='结束时间')
    total_count = Column(Integer, default=0, comment='总数')
    success_count = Column(Integer, default=0, comment='成功数')
    fail_count = Column(Integer, default=0, comment='失败数')
    status = Column(String(50), default='running', comment='状态')
    error_message = Column(Text, comment='错误消息')
    
    # 索引
    __table_args__ = (
        Index('idx_update_type', 'update_type'),
        Index('idx_status', 'status'),
        Index('idx_start_time', 'start_time'),
    )


class JobLog(Base):
    """定时任务执行日志表"""
    __tablename__ = 'job_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment='日志ID')
    user_id = Column(Integer, comment='所属用户ID')
    job_type = Column(String(100), nullable=False, comment='任务类型')
    job_name = Column(String(200), nullable=False, comment='任务名称')
    status = Column(String(50), nullable=False, comment='状态')
    started_at = Column(DateTime, nullable=False, comment='开始时间')
    completed_at = Column(DateTime, comment='完成时间')
    duration = Column(Float(10, 4), comment='执行时长（秒）')
    message = Column(Text, comment='消息')
    error = Column(Text, comment='错误信息')
    
    # 索引
    __table_args__ = (
        Index('idx_job_type', 'job_type'),
        Index('idx_status', 'status'),
        Index('idx_started_at', 'started_at'),
        Index('idx_job_logs_user_id', 'user_id'),
    )


class TaskExecutionDetail(Base):
    """任务执行详细结果表"""
    __tablename__ = 'task_execution_details'
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment='详情ID')
    job_log_id = Column(Integer, nullable=False, comment='任务日志ID')
    task_type = Column(String(100), nullable=False, comment='任务类型')
    stock_code = Column(String(20), comment='股票代码')
    stock_name = Column(String(500), comment='股票名称')
    detail_type = Column(String(100), nullable=False, comment='详情类型')
    detail_data = Column(Text, nullable=False, comment='详情数据（JSON格式）')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    
    # 索引
    __table_args__ = (
        Index('idx_job_log_id', 'job_log_id'),
        Index('idx_task_type', 'task_type'),
        Index('idx_stock_code', 'stock_code'),
        Index('idx_detail_type', 'detail_type'),
    )


class DailyMarket(Base):
    """股票日线行情数据表"""
    __tablename__ = 'daily_market'
    
    code = Column(String(20), primary_key=True, comment='股票代码')
    trade_date = Column(Date, primary_key=True, comment='交易日期')
    open = Column(Numeric(10, 2), comment='开盘价')
    close = Column(Numeric(10, 2), comment='收盘价')
    high = Column(Numeric(10, 2), comment='最高价')
    low = Column(Numeric(10, 2), comment='最低价')
    volume = Column(BigInteger, comment='成交量')
    amount = Column(Numeric(20, 2), comment='成交额')
    change_pct = Column(Numeric(10, 2), comment='涨跌幅')
    turnover_rate = Column(Numeric(10, 2), comment='换手率')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    
    # 索引
    __table_args__ = (
        Index('idx_daily_market_code', 'code'),
        Index('idx_daily_market_date', 'trade_date'),
        Index('idx_daily_market_code_date', 'code', 'trade_date'),
        {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}
    )




class ORMDatabase:
    """SQLAlchemy ORM 数据库管理类"""
    
    def __init__(self, db_url: str):
        """
        初始化数据库连接
        
        Args:
            db_url: 数据库连接URL
        """
        self.db_url = db_url
        
        # 创建引擎
        self.engine = create_engine(
            db_url,
            echo=False,  # 不输出SQL日志
            pool_pre_ping=True,  # 连接前检测
            pool_recycle=3600,  # 连接回收时间
            pool_size=10,  # 连接池大小
            max_overflow=20  # 最大溢出连接数
        )
        
        # 创建会话工厂
        self.Session = sessionmaker(bind=self.engine)
        
        # 创建所有表
        self._create_tables()
        
        logger.info(f"ORM数据库初始化完成: {db_url}")
    
    def _create_tables(self):
        """创建所有表"""
        import re
        from sqlalchemy import text
        
        # 先创建数据库（如果不存在）
        self._create_database_if_not_exists()
        
        # 然后创建所有表
        Base.metadata.create_all(self.engine)
    
    def _create_database_if_not_exists(self):
        """如果数据库不存在则创建"""
        from sqlalchemy import text, create_engine
        
        # 从 db_url 中提取数据库信息
        # 格式: mysql+pymysql://user:password@host:port/database
        match = re.match(
            r'mysql\+pymysql://([^:]+):([^@]+)@([^:]+):(\d+)/([^?]+)',
            self.db_url
        )
        
        if not match:
            logger.warning("无法解析数据库URL，跳过数据库创建")
            return
        
        username, password, host, port, database = match.groups()
        
        # 创建一个不指定数据库的连接URL，用于连接到MySQL服务器
        server_url = f"mysql+pymysql://{username}:{password}@{host}:{port}"
        
        try:
            # 连接到MySQL服务器
            server_engine = create_engine(server_url, isolation_level="AUTOCOMMIT")
            
            with server_engine.connect() as conn:
                # 检查数据库是否存在
                result = conn.execute(text(
                    f"SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = '{database}'"
                ))
                
                if not result.fetchone():
                    # 数据库不存在，创建它
                    logger.info(f"数据库 '{database}' 不存在，正在创建...")
                    conn.execute(text(f"CREATE DATABASE `{database}` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
                    logger.info(f"数据库 '{database}' 创建成功")
                else:
                    logger.info(f"数据库 '{database}' 已存在")
            
            server_engine.dispose()
            
        except Exception as e:
            logger.error(f"创建数据库失败: {e}")
            raise
    
    def get_session(self):
        """
        获取数据库会话
        
        Returns:
            Session: SQLAlchemy会话对象
        """
        return self.Session()
    
    def execute_query(self, query: str, params: tuple = None) -> list:
        """
        执行原生SQL查询（为了兼容现有代码）
        
        Args:
            query: SQL查询语句
            params: 查询参数
            
        Returns:
            查询结果列表
        """
        from sqlalchemy import text
        
        session = self.get_session()
        try:
            # 将 SQLite 的 ? 占位符转换为 SQLAlchemy 的 :param 格式
            # 如果参数是 tuple，转换为命名参数格式
            if params:
                # 将 ? 替换为 :p1, :p2, :p3 等（使用字母开头）
                param_names = [f'p{i+1}' for i in range(len(params))]
                query_text = query
                for i, param_name in enumerate(param_names):
                    query_text = query_text.replace('?', f':{param_name}', 1)
                
                # 构建参数字典
                param_dict = {param_names[i]: params[i] for i in range(len(params))}
                result = session.execute(text(query_text), param_dict)
            else:
                result = session.execute(text(query))
            
            # 获取列名
            columns = result.keys()
            
            # 转换为字典列表
            results = [dict(zip(columns, row)) for row in result.fetchall()]
            return results
        finally:
            session.close()
    
    def execute_update(self, query: str, params: tuple = None) -> int:
        """
        执行原生SQL更新（为了兼容现有代码）
        
        Args:
            query: SQL更新语句
            params: 更新参数
            
        Returns:
            影响的行数
        """
        from sqlalchemy import text
        
        session = self.get_session()
        try:
            if params:
                # 将 ? 替换为 :param 格式（使用字母开头）
                param_names = [f'p{i+1}' for i in range(len(params))]
                query_text = query
                for i, param_name in enumerate(param_names):
                    query_text = query_text.replace('?', f':{param_name}', 1)
                
                param_dict = {param_names[i]: params[i] for i in range(len(params))}
                result = session.execute(text(query_text), param_dict)
            else:
                result = session.execute(text(query))
            session.commit()
            return result.rowcount
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    def execute_many(self, query: str, params_list: list) -> int:
        """
        批量执行更新语句
        
        Args:
            query: SQL更新语句
            params_list: 参数列表
            
        Returns:
            影响的行数
        """
        from sqlalchemy import text
        
        session = self.get_session()
        try:
            # 将 ? 替换为 :param 格式（只替换第一个参数中的）
            if params_list:
                param_count = len(params_list[0])
                param_names = [f'p{i+1}' for i in range(param_count)]
                query_text = query
                for i, param_name in enumerate(param_names):
                    query_text = query_text.replace('?', f':{param_name}', 1)
                
                # 转换所有参数为字典列表
                param_dicts = [{param_names[i]: params[i] for i in range(param_count)} for params in params_list]
                result = session.execute(text(query_text), param_dicts)
            else:
                result = session.execute(text(query))
            
            session.commit()
            return result.rowcount
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    def insert_one(self, table: str, data: dict) -> int:
        """
        插入单条记录（使用ORM）
        
        Args:
            table: 表名
            data: 数据字典
            
        Returns:
            插入记录的ID
        """
        session = self.get_session()
        try:
            # 根据表名获取模型类
            model_class = self._get_model_class(table)
            if model_class:
                obj = model_class(**data)
                session.add(obj)
                session.commit()
                session.refresh(obj)
                return getattr(obj, 'id', 0)
            else:
                # 如果没有对应的ORM模型，使用原生SQL
                columns = ', '.join(data.keys())
                placeholders = ', '.join(['?' for _ in data])
                query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
                result = session.execute(query, tuple(data.values()))
                session.commit()
                return result.lastrowid
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    def update_one(self, table: str, data: dict, where: dict) -> int:
        """
        更新记录（使用ORM）
        
        Args:
            table: 表名
            data: 要更新的数据字典
            where: 条件字典
            
        Returns:
            影响的行数
        """
        session = self.get_session()
        try:
            # 根据表名获取模型类
            model_class = self._get_model_class(table)
            if model_class:
                # 使用ORM更新
                query = session.query(model_class)
                
                # 添加过滤条件
                for key, value in where.items():
                    query = query.filter(getattr(model_class, key) == value)
                
                # 执行更新
                count = query.update(data)
                session.commit()
                return count
            else:
                # 如果没有对应的ORM模型，使用原生SQL
                set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
                where_clause = ' AND '.join([f"{k} = ?" for k in where.keys()])
                query = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
                params = tuple(data.values()) + tuple(where.values())
                result = session.execute(query, params)
                session.commit()
                return result.rowcount
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    def delete(self, table: str, where: dict) -> int:
        """
        删除记录（使用ORM）
        
        Args:
            table: 表名
            where: 条件字典
            
        Returns:
            影响的行数
        """
        session = self.get_session()
        try:
            # 根据表名获取模型类
            model_class = self._get_model_class(table)
            if model_class:
                # 使用ORM删除
                query = session.query(model_class)
                
                # 添加过滤条件
                for key, value in where.items():
                    query = query.filter(getattr(model_class, key) == value)
                
                # 执行删除
                count = query.delete()
                session.commit()
                return count
            else:
                # 如果没有对应的ORM模型，使用原生SQL
                where_clause = ' AND '.join([f"{k} = ?" for k in where.keys()])
                query = f"DELETE FROM {table} WHERE {where_clause}"
                result = session.execute(query, tuple(where.values()))
                session.commit()
                return result.rowcount
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    def _get_model_class(self, table_name: str):
        """
        根据表名获取对应的ORM模型类
        
        Args:
            table_name: 表名
            
        Returns:
            ORM模型类或None
        """
        model_map = {
            'users': User,
            'stocks': Stock,
            'strategies': Strategy,
            'strategy_results': StrategyResult,
            'system_logs': SystemLog,
            'data_update_history': DataUpdateHistory,
            'job_logs': JobLog,
            'task_execution_details': TaskExecutionDetail,
            'daily_market': DailyMarket,
        }
        return model_map.get(table_name)
    
    def close(self):
        """关闭数据库连接"""
        self.engine.dispose()
