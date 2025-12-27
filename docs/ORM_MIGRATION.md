# MySQL ORM 重构说明文档

## 概述

本次重构为 MySQL 和 SQLite 数据库引入了 **SQLAlchemy ORM** 支持，同时保持 DuckDB 的原生 SQL 访问方式。

## 主要变更

### 1. 新增文件

#### `app/models/orm_models.py`
- 定义了所有数据库表的 ORM 模型类：
  - `Stock` - 股票基础信息
  - `Strategy` - 策略配置
  - `StrategyResult` - 策略执行结果
  - `SystemLog` - 系统日志
  - `DataUpdateHistory` - 数据更新历史
  - `JobLog` - 任务日志
  - `TaskExecutionDetail` - 任务执行详情
- `ORMDatabase` 类：提供 ORM 数据库管理
- 自动处理 SQLite 的 `?` 占位符与 SQLAlchemy 的参数绑定兼容

#### `app/models/orm_db.py`
- `ORMDBAdapter` 类：ORM 数据库适配器
- 提供与原有数据库接口完全兼容的 API：
  - `execute_query()` - 执行查询
  - `execute_update()` - 执行更新
  - `execute_many()` - 批量执行
  - `insert_one()` - 插入记录
  - `update_one()` - 更新记录
  - `delete()` - 删除记录
- `get_session()` - 获取 SQLAlchemy 会话，用于直接 ORM 操作

#### `scripts/migrate_to_mysql.py`
- 数据迁移脚本：将 SQLite 数据迁移到 MySQL
- 支持批量迁移、外键约束检查、错误处理

#### `scripts/test_orm.py`
- ORM 功能测试脚本
- 验证数据库连接、增删改查、ORM 模型操作

### 2. 修改文件

#### `app/models/database_factory.py`
- 新增 `ORMDBAdapter` 导入
- `get_database()` 方法新增 `use_orm` 参数（默认为 `True`）
- 对于 MySQL 和 SQLite，默认使用 ORM 模式
- 保持向后兼容，可通过 `use_orm=False` 使用原生 SQL 模式

#### `app/models/__init__.py`
- 导出所有 ORM 模型类和适配器

#### `requirements.txt`
- 新增依赖：
  - `SQLAlchemy==2.0.23` - ORM 框架
  - `pymysql==1.1.0` - MySQL 驱动
  - `cryptography==41.0.7` - 加密库
  - `dbutils==3.0.0` - 数据库连接池工具

## 使用方式

### 1. 使用 ORM 模式（默认）

```python
from app.models.database_factory import get_database

# 自动使用 ORM（MySQL 或 SQLite）
db = get_database()

# 兼容原有接口，支持 ? 占位符
result = db.execute_query("SELECT * FROM stocks WHERE status = ?", ('normal',))
```

### 2. 直接使用 ORM 模型

```python
from app.models.orm_models import Stock, Strategy
from app.models.orm_db import ORMDBAdapter
from app.utils import get_config

# 获取 ORM 数据库
config = get_config()
mysql_config = config.get('database.mysql')
mysql_db = ORMDBAdapter('mysql', mysql_config)

# 使用 SQLAlchemy 会话
session = mysql_db.get_session()

# 使用 ORM 查询
stocks = session.query(Stock).filter(Stock.status == 'normal').limit(10).all()
strategies = session.query(Strategy).filter(Strategy.enabled == True).all()

# 使用 ORM 插入
new_stock = Stock(
    code='600000',
    name='浦发银行',
    industry='银行',
    status='normal'
)
session.add(new_stock)
session.commit()

# 使用 ORM 更新
stock = session.query(Stock).filter(Stock.code == '600000').first()
stock.name = '浦发银行（更新）'
session.commit()

# 使用 ORM 删除
session.query(Stock).filter(Stock.code == '600000').delete()
session.commit()

session.close()
```

### 3. DuckDB 继续使用原生 SQL

```python
from app.models import get_duckdb

duckdb = get_duckdb()

# 直接使用 SQL 查询
result = duckdb.execute_query("""
    SELECT code, trade_date, close
    FROM daily_market
    WHERE code = ? AND trade_date >= ?
    ORDER BY trade_date DESC
    LIMIT 10
""", ('000001', '2024-01-01'))
```

## 数据迁移

### 从 SQLite 迁移到 MySQL

```bash
# 确保配置文件中 MySQL 连接信息正确
# config.yaml
database:
  type: mysql
  mysql:
    host: localhost
    port: 3306
    database: stock_analysis
    username: stock_user
    password: your_password

# 执行迁移脚本
python3 scripts/migrate_to_mysql.py
```

### 迁移说明

迁移脚本会：
1. 自动从 SQLite 读取所有数据
2. 转换数据格式（日期、时间等）
3. 检查外键约束，跳过无效记录
4. 批量写入 MySQL
5. 提供详细的迁移日志

## 配置说明

### MySQL 配置

```yaml
database:
  type: mysql  # 或 sqlite
  mysql:
    host: localhost
    port: 3306
    database: stock_analysis
    username: stock_user
    password: your_password
    pool:
      size: 50
      max_overflow: 10
      timeout: 30
      recycle: 3600
    charset: utf8mb4
    collation: utf8mb4_unicode_ci
```

### SQLite 配置

```yaml
database:
  type: sqlite
  sqlite_path: ./data/stock_analysis.db
```

### DuckDB 配置

```yaml
database:
  duckdb_path: ./data/market_data.duckdb
```

## 测试

### 运行测试脚本

```bash
python3 scripts/test_orm.py
```

测试内容：
- ✅ 数据库连接测试
- ✅ 查询操作测试
- ✅ 插入、更新、删除测试
- ✅ ORM 模型直接访问测试

## 启动应用

```bash
# 启动 API 服务
python3 app/api/app.py

# 启动 Web 服务
python3 app/web/app.py
```

## 优势

### 使用 ORM 的好处

1. **类型安全**：ORM 模型提供类型检查和 IDE 自动补全
2. **防止 SQL 注入**：自动处理参数绑定
3. **跨数据库兼容**：自动适配不同数据库的 SQL 方言
4. **代码更清晰**：使用 Python 对象而非 SQL 字符串
5. **关系映射**：自动处理表之间的外键关系
6. **事务管理**：自动处理提交和回滚

### DuckDB 保持原生 SQL 的好处

1. **高性能**：DuckDB 是列式数据库，原生 SQL 性能最佳
2. **简单直接**：对于分析查询，SQL 更直观
3. **灵活性**：支持复杂的分析函数和窗口函数

## 注意事项

1. **外键约束**：迁移时会跳过引用不存在的外键记录
2. **日期格式**：ORM 自动处理日期格式的转换
3. **连接池**：ORM 使用连接池管理数据库连接
4. **会话管理**：使用 `get_session()` 获取的会话需要手动关闭
5. **参数绑定**：ORM 适配器自动将 SQLite 的 `?` 占位符转换为 SQLAlchemy 支持的格式

## 故障排查

### 数据库连接失败

1. 检查 MySQL 服务是否运行
2. 验证配置文件中的连接信息
3. 确认数据库用户权限

### ORM 报错

1. 确认所有依赖已安装：`pip install -r requirements.txt`
2. 查看日志文件：`logs/app.log`
3. 运行测试脚本：`python3 scripts/test_orm.py`

### 数据迁移失败

1. 检查 SQLite 数据库是否存在
2. 确认 MySQL 数据库已创建
3. 查看迁移脚本的错误日志

## 后续优化建议

1. **性能优化**：
   - 为常用查询添加索引
   - 使用批量操作减少数据库调用
   - 考虑使用 SQLAlchemy 的查询缓存

2. **代码重构**：
   - 将复杂查询迁移到 ORM 模型方法
   - 使用 SQLAlchemy 的关系映射简化代码
   - 添加更完整的模型验证

3. **监控**：
   - 添加慢查询日志
   - 监控数据库连接池使用情况
   - 定期检查数据库性能指标

## 总结

✅ **已完成的任务**：
- 使用 SQLAlchemy ORM 重构 MySQL 和 SQLite 访问
- 保持 DuckDB 原生 SQL 访问方式
- 实现 SQLite 到 MySQL 的数据迁移
- 提供完整的向后兼容性
- 添加测试脚本验证功能

🎯 **核心优势**：
- MySQL/SQLite 使用 ORM：类型安全、防止 SQL 注入、跨数据库兼容
- DuckDB 使用原生 SQL：高性能、简单直接
- 无缝切换：通过配置文件即可切换数据库类型
