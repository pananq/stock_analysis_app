"""
SQLAlchemy ORM 模型定义
用于 MySQL 和 SQLite 数据库的 ORM 操作
"""
import re
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, DateTime,
    Date, Boolean, Float, Index, Numeric, BigInteger, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from app.utils import get_logger

logger = get_logger(__name__)

# 声明基类
Base = declarative_base()
SecurityId = BigInteger().with_variant(Integer, 'sqlite')


class Stock(Base):
    """股票基础信息表"""
    __tablename__ = 'stocks'
    
    id = Column(SecurityId, primary_key=True, autoincrement=True, comment='证券ID')
    code = Column(String(20), nullable=False, comment='市场内证券代码')
    market = Column(
        String(10),
        nullable=False,
        default='CN',
        comment='标准市场(CN/HK/US)',
    )
    name = Column(String(500), nullable=False, comment='股票名称')
    list_date = Column(Date, comment='上市日期')
    industry = Column(String(200), comment='所属行业')
    market_type = Column(String(50), comment='市场类型')
    security_type = Column(
        String(20),
        nullable=False,
        default='STOCK',
        comment='证券类型(STOCK/ETF/FUND/INDEX)',
    )
    status = Column(String(50), default='normal', comment='状态')
    earliest_data_date = Column(Date, comment='最早数据日期')
    latest_data_date = Column(Date, comment='最近数据日期')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    
    # 索引
    __table_args__ = (
        UniqueConstraint(
            'market',
            'code',
            'security_type',
            name='uq_stocks_market_code_type',
        ),
        Index('idx_stocks_code', 'code'),
        Index('idx_stocks_market', 'market'),
        Index('idx_status', 'status'),
        Index('idx_industry', 'industry'),
        Index('idx_market_type', 'market_type'),
        Index('idx_security_type', 'security_type'),
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
    nickname = Column(String(50), comment='个人昵称')
    email = Column(String(254), comment='每日日报收件邮箱')
    daily_report_enabled = Column(
        Boolean,
        nullable=False,
        default=False,
        comment='是否启用个人邮件日报',
    )
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
    security_id = Column(SecurityId, comment='证券ID')
    stock_code = Column(String(20), nullable=False, comment='股票代码')
    trigger_date = Column(Date, nullable=False, comment='触发日期')
    trigger_price = Column(Float(10, 4), comment='触发价格')
    rise_percent = Column(Float(10, 4), comment='涨幅')
    result_data = Column(Text, comment='结果数据（JSON格式）')
    executed_at = Column(DateTime, default=datetime.now, comment='执行时间')
    
    # 索引
    __table_args__ = (
        Index('idx_strategy_id', 'strategy_id'),
        Index('idx_strategy_result_security_id', 'security_id'),
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
    
    security_id = Column(SecurityId, primary_key=True, comment='证券ID')
    trade_date = Column(Date, primary_key=True, comment='交易日期')
    code = Column(String(20), nullable=False, comment='冗余证券代码（兼容展示）')
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
        {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}
    )




class Watchlist(Base):
    """自选股表"""
    __tablename__ = 'watchlists'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='自选股ID')
    user_id = Column(Integer, nullable=False, comment='用户ID')
    security_id = Column(SecurityId, nullable=False, comment='证券ID')
    stock_code = Column(String(20), nullable=False, comment='股票代码')
    market = Column(String(20), nullable=False, default='CN', comment='市场')
    security_type = Column(
        String(20),
        nullable=False,
        default='STOCK',
        comment='证券类型',
    )
    group_name = Column(String(100), comment='分组名称')
    tags = Column(String(500), comment='标签，格式,tag1,tag2,')
    notes = Column(String(500), comment='备注')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')

    __table_args__ = (
        UniqueConstraint(
            'user_id',
            'security_id',
            name='uq_watchlist_user_security',
        ),
        Index('idx_watchlist_security_id', 'security_id'),
        Index('idx_watchlist_group_name', 'group_name'),
        Index('idx_watchlist_stock_code', 'stock_code'),
    )


class ApiToken(Base):
    """API Token表"""
    __tablename__ = 'api_tokens'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='TokenID')
    user_id = Column(Integer, nullable=False, comment='用户ID')
    name = Column(String(100), nullable=False, comment='Token名称')
    token_hash = Column(String(255), nullable=False, unique=True, comment='Token哈希')
    token_prefix = Column(String(10), nullable=False, comment='Token前缀')
    is_active = Column(Boolean, default=True, comment='是否有效')
    last_used_at = Column(DateTime, comment='最后使用时间')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')

    __table_args__ = (
        Index('idx_api_tokens_user_id', 'user_id'),
        Index('idx_api_tokens_prefix', 'token_prefix'),
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
        
        # 从配置中获取连接池参数
        try:
            from app.utils import get_config
            config = get_config()
            pool_config = config.get('database', {}).get('mysql', {}).get('pool', {})
            
            pool_size = pool_config.get('size', 10)
            max_overflow = pool_config.get('max_overflow', 20)
            pool_timeout = pool_config.get('timeout', 30)
            pool_recycle = pool_config.get('recycle', 3600)
            
            logger.info(f"使用连接池配置: size={pool_size}, max_overflow={max_overflow}, timeout={pool_timeout}, recycle={pool_recycle}")
        except Exception as e:
            logger.warning(f"获取连接池配置失败，使用默认值: {e}")
            pool_size = 10
            max_overflow = 20
            pool_timeout = 30
            pool_recycle = 3600
        
        # 创建引擎
        self.engine = create_engine(
            db_url,
            echo=False,  # 不输出SQL日志
            pool_pre_ping=True,  # 连接前检测，自动回收无效连接
            pool_recycle=pool_recycle,  # 连接回收时间（秒）
            pool_size=pool_size,  # 连接池大小
            max_overflow=max_overflow,  # 最大溢出连接数
            pool_timeout=pool_timeout,  # 获取连接的超时时间
            connect_args={
                'connect_timeout': 10,  # 连接超时
                'read_timeout': 30,  # 读取超时
                'write_timeout': 30,  # 写入超时
            }
        )
        
        # 创建会话工厂
        self.Session = sessionmaker(bind=self.engine)
        
        # 创建所有表
        self._create_tables()
        
        safe_url = self.engine.url.render_as_string(hide_password=True)
        logger.info(f"ORM数据库初始化完成: {safe_url}")
    
    def _create_tables(self):
        """创建所有表"""
        import re
        from sqlalchemy import text
        
        # 先创建数据库（如果不存在）
        self._create_database_if_not_exists()
        
        # 然后创建所有表
        Base.metadata.create_all(self.engine)
        self._migrate_security_type_columns()
        self._migrate_user_profile_columns()

    def _migrate_security_type_columns(self):
        """为已有数据库补充证券类型字段。"""
        from sqlalchemy import inspect, text

        inspector = inspect(self.engine)
        with self.engine.begin() as connection:
            stock_columns = {
                column['name']
                for column in inspector.get_columns('stocks')
            }
            if 'security_type' not in stock_columns:
                connection.execute(text(
                    "ALTER TABLE stocks ADD COLUMN security_type "
                    "VARCHAR(20) NOT NULL DEFAULT 'STOCK'"
                ))
                connection.execute(text(
                    "CREATE INDEX idx_security_type "
                    "ON stocks (security_type)"
                ))

            watchlist_columns = {
                column['name']
                for column in inspector.get_columns('watchlists')
            }
            if 'security_type' not in watchlist_columns:
                connection.execute(text(
                    "ALTER TABLE watchlists ADD COLUMN security_type "
                    "VARCHAR(20) NOT NULL DEFAULT 'STOCK'"
                ))

    def _migrate_user_profile_columns(self):
        """为已有用户表补充可选的个人资料字段。"""
        from sqlalchemy import inspect, text

        inspector = inspect(self.engine)
        user_columns = {
            column['name']
            for column in inspector.get_columns('users')
        }
        with self.engine.begin() as connection:
            if 'nickname' not in user_columns:
                connection.execute(text(
                    "ALTER TABLE users ADD COLUMN nickname VARCHAR(50) NULL"
                ))
            if 'email' not in user_columns:
                connection.execute(text(
                    "ALTER TABLE users ADD COLUMN email VARCHAR(254) NULL"
                ))
            if 'daily_report_enabled' not in user_columns:
                connection.execute(text(
                    "ALTER TABLE users ADD COLUMN daily_report_enabled "
                    "TINYINT(1) NOT NULL DEFAULT 0"
                ))
    
    def _create_database_if_not_exists(self):
        """如果数据库不存在则创建"""
        from sqlalchemy import text, create_engine
        from sqlalchemy.engine import make_url

        parsed_url = make_url(self.db_url)
        if parsed_url.get_backend_name() != 'mysql':
            return

        database = parsed_url.database
        if not database or not re.fullmatch(r'[A-Za-z0-9_]+', database):
            raise ValueError("MySQL 数据库名只能包含字母、数字和下划线")

        # URL 对象会正确转义用户名和密码中的 @、:、/ 等字符。
        server_url = parsed_url.set(database=None)
        
        try:
            # 连接到MySQL服务器
            server_engine = create_engine(server_url, isolation_level="AUTOCOMMIT")
            
            with server_engine.connect() as conn:
                # 检查数据库是否存在
                result = conn.execute(
                    text(
                        "SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA "
                        "WHERE SCHEMA_NAME = :database"
                    ),
                    {'database': database},
                )
                
                if not result.fetchone():
                    # 数据库不存在，创建它
                    logger.info(f"数据库 '{database}' 不存在，正在创建...")
                    conn.exec_driver_sql(
                        f"CREATE DATABASE `{database}` DEFAULT CHARACTER SET "
                        "utf8mb4 COLLATE utf8mb4_unicode_ci"
                    )
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
        支持自动重试机制
        
        Args:
            query: SQL查询语句
            params: 查询参数
            
        Returns:
            查询结果列表
        """
        from sqlalchemy import text
        from app.utils.db_retry import retry_db_operation
        
        @retry_db_operation(max_retries=3, retry_delay=0.5)
        def _execute():
            session = self.get_session()
            try:
                # 将 SQLite 的 ? 或 MySQL 的 %s 占位符转换为 SQLAlchemy 的 :param 格式
                # 如果参数是 tuple，转换为命名参数格式
                if params:
                    # 检测使用哪种占位符
                    if '%' in query and '%s' in query:
                        # 使用 %s 占位符（MySQL 格式）
                        param_names = [f'p{i+1}' for i in range(len(params))]
                        query_text = query
                        for i, param_name in enumerate(param_names):
                            query_text = query_text.replace('%s', f':{param_name}', 1)
                    else:
                        # 使用 ? 占位符（SQLite 格式）
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
            except Exception as e:
                logger.error(f"执行查询失败: {e}, Query: {query[:100]}")
                raise
            finally:
                try:
                    session.close()
                except Exception as e:
                    logger.warning(f"关闭会话失败: {e}")
        
        return _execute()
    
    def execute_update(self, query: str, params: tuple = None) -> int:
        """
        执行原生SQL更新（为了兼容现有代码）
        支持自动重试机制
        
        Args:
            query: SQL更新语句
            params: 更新参数
            
        Returns:
            影响的行数
        """
        from sqlalchemy import text
        from app.utils.db_retry import retry_db_operation
        
        @retry_db_operation(max_retries=3, retry_delay=0.5)
        def _execute():
            session = self.get_session()
            try:
                if params:
                    # 将 ? 或 %s 替换为 :param 格式（使用字母开头）
                    param_names = [f'p{i+1}' for i in range(len(params))]
                    query_text = query
                    
                    # 检测使用哪种占位符
                    if '%' in query and '%s' in query:
                        # 使用 %s 占位符（MySQL 格式）
                        for i, param_name in enumerate(param_names):
                            query_text = query_text.replace('%s', f':{param_name}', 1)
                    else:
                        # 使用 ? 占位符（SQLite 格式）
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
        
        return _execute()
    
    def execute_many(self, query: str, params_list: list) -> int:
        """
        批量执行更新语句
        支持自动重试机制
        
        Args:
            query: SQL更新语句
            params_list: 参数列表
            
        Returns:
            影响的行数
        """
        from sqlalchemy import text
        from app.utils.db_retry import retry_db_operation
        
        @retry_db_operation(max_retries=3, retry_delay=0.5)
        def _execute():
            session = self.get_session()
            try:
                # 将 ? 或 %s 替换为 :param 格式（只替换第一个参数中的）
                if params_list:
                    param_count = len(params_list[0])
                    param_names = [f'p{i+1}' for i in range(param_count)]
                    query_text = query
                    
                    # 检测使用哪种占位符
                    if '%' in query and '%s' in query:
                        # 使用 %s 占位符（MySQL 格式）
                        for i, param_name in enumerate(param_names):
                            query_text = query_text.replace('%s', f':{param_name}', 1)
                    else:
                        # 使用 ? 占位符（SQLite 格式）
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
        
        return _execute()
    
    def insert_one(self, table: str, data: dict) -> int:
        """
        插入单条记录（使用ORM）
        支持自动重试机制
        
        Args:
            table: 表名
            data: 数据字典
            
        Returns:
            插入记录的ID
        """
        from app.utils.db_retry import retry_db_operation
        
        @retry_db_operation(max_retries=3, retry_delay=0.5)
        def _execute():
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
        
        return _execute()
    
    def update_one(self, table: str, data: dict, where: dict) -> int:
        """
        更新记录（使用ORM）
        支持自动重试机制
        
        Args:
            table: 表名
            data: 要更新的数据字典
            where: 条件字典
            
        Returns:
            影响的行数
        """
        from app.utils.db_retry import retry_db_operation
        
        @retry_db_operation(max_retries=3, retry_delay=0.5)
        def _execute():
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
        
        return _execute()
    
    def delete(self, table: str, where: dict) -> int:
        """
        删除记录（使用ORM）
        支持自动重试机制
        
        Args:
            table: 表名
            where: 条件字典
            
        Returns:
            影响的行数
        """
        from app.utils.db_retry import retry_db_operation
        
        @retry_db_operation(max_retries=3, retry_delay=0.5)
        def _execute():
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
        
        return _execute()
    
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
            'watchlists': Watchlist,
            'api_tokens': ApiToken,
        }
        return model_map.get(table_name)
    
    def close(self):
        """关闭数据库连接"""
        self.engine.dispose()
