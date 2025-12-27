# 数据库文档

本目录包含股票分析系统的数据库Schema说明和建表SQL语句。

## 数据库架构

本项目采用多数据库架构，分别用于不同的数据场景：

- **SQLite**: 存储元数据和配置信息（默认数据库）
- **DuckDB**: 存储历史行情数据，支持高效分析查询
- **MySQL 8.0**: 企业级数据库，支持高并发和大规模数据（可选）

```
┌─────────────────────────┐         ┌─────────────────────────┐
│                         │         │                         │
│   SQLite                │         │   DuckDB                │
│   stock_analysis.db     │         │   market_data.duckdb    │
│                         │         │                         │
│  - stocks               │         │  - daily_market         │
│  - strategies           │◄────────┤  (历史行情数据)          │
│  - strategy_results     │         │                         │
│  - system_logs          │         │  高性能OLAP查询          │
│  - data_update_history  │         │  列式存储                │
│  - job_logs             │         │  向量化执行              │
│  - task_execution_details│         │  并行查询                │
│                         │         │                         │
│  事务处理、轻量级       │         │  分析查询、大数据量       │
└─────────────────────────┘         └─────────────────────────┘
                                           │
                                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   MySQL 8.0 (可选，可替代SQLite)                                │
│   stock_analysis                                                │
│                                                                 │
│  - stocks                                                       │
│  - strategies                                                   │
│  - strategy_results                                             │
│  - system_logs                                                  │
│  - data_update_history                                          │
│  - job_logs                                                     │
│  - task_execution_details                                       │
│                                                                 │
│  高并发、连接池、事务管理、企业级                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 数据库选择

### SQLite（默认）

- **适用场景**: 开发环境、小规模数据、单机部署
- **优点**: 轻量级、无需配置、零运维
- **限制**: 并发性能有限、不适合大规模数据

### DuckDB（必需）

- **适用场景**: 历史行情数据存储和分析
- **优点**: 高性能OLAP查询、列式存储、向量化执行
- **用途**: 存储和查询历史行情数据

### MySQL 8.0（可选）

- **适用场景**: 生产环境、大规模数据、高并发访问
- **优点**: 企业级、高并发、连接池、事务管理
- **迁移**: 支持从SQLite无缝迁移

## 文件列表

### SQLite 数据库文档

1. **[sqlite_schema.md](./sqlite_schema.md)** - SQLite数据库Schema详细说明
   - 7个数据表的详细描述
   - 字段定义、约束、索引
   - 外键关系和数据完整性
   - 使用场景和性能优化建议

2. **[sqlite_create_tables.sql](./sqlite_create_tables.sql)** - SQLite建表SQL脚本
   - 完整的CREATE TABLE语句
   - 索引创建语句
   - 示例数据插入
   - 常用查询示例

### DuckDB 数据库文档

1. **[duckdb_schema.md](./duckdb_schema.md)** - DuckDB数据库Schema详细说明
   - daily_market表详细描述
   - 数据特点和使用场景
   - 10个常用查询示例
   - 性能优化建议

2. **[duckdb_create_tables.sql](./duckdb_create_tables.sql)** - DuckDB建表SQL脚本
   - CREATE TABLE语句
   - 索引创建语句
   - 示例数据插入
   - 10个常用查询示例
   - 数据维护命令

### MySQL 8.0 数据库文档

1. **[mysql_schema.md](./mysql_schema.md)** - MySQL数据库Schema详细说明
   - 7个数据表的详细描述
   - 字段定义、约束、索引
   - 外键关系和数据完整性
   - 性能优化建议

2. **[mysql_create_tables.sql](./mysql_create_tables.sql)** - MySQL建表SQL脚本
   - 完整的CREATE TABLE语句
   - 索引创建语句
   - 外键约束
   - 字符集和排序规则配置

### 迁移相关文档

1. **[mysql-migration-guide.md](../mysql-migration-guide.md)** - MySQL迁移指南
   - 从SQLite迁移到MySQL的完整流程
   - 迁移工具使用说明
   - 数据验证方法
   - 常见问题解答

2. **[mysql-rollback-guide.md](../mysql-rollback-guide.md)** - MySQL回滚指南
   - 从MySQL回滚到SQLite的流程
   - 回滚工具使用说明
   - 备份和恢复方法
   - 故障排查指南

## 快速开始

### 1. 创建SQLite数据库（默认）

```bash
# 使用SQLite命令行工具
sqlite3 data/stock_analysis.db < docs/database/sqlite_create_tables.sql

# 或在Python中使用
python3 << 'EOF'
import sqlite3

# 读取SQL脚本
with open('docs/database/sqlite_create_tables.sql', 'r', encoding='utf-8') as f:
    sql_script = f.read()

# 执行SQL脚本
conn = sqlite3.connect('data/stock_analysis.db')
conn.executescript(sql_script)
conn.close()
print("SQLite数据库创建成功！")
EOF
```

### 2. 创建DuckDB数据库（必需）

```bash
# 使用Python
python3 << 'EOF'
import duckdb

# 读取SQL脚本
with open('docs/database/duckdb_create_tables.sql', 'r', encoding='utf-8') as f:
    sql_script = f.read()

# 执行SQL脚本
conn = duckdb.connect('data/market_data.duckdb')
conn.executescript(sql_script)
conn.close()
print("DuckDB数据库创建成功！")
EOF
```

### 3. 创建MySQL数据库（可选）

#### 方式一：使用Python自动创建

配置 `config.yaml` 后启动应用，会自动创建表：

```yaml
database:
  type: mysql
  mysql:
    host: localhost
    port: 3306
    database: stock_analysis
    username: your_username
    password: your_password
```

#### 方式二：使用SQL脚本手动创建

```bash
# 创建数据库
mysql -u root -p -e "CREATE DATABASE stock_analysis DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 执行建表脚本
mysql -u your_username -p stock_analysis < docs/database/mysql_create_tables.sql
```

### 4. 验证数据库创建

```bash
# 验证SQLite
sqlite3 data/stock_analysis.db "SELECT name FROM sqlite_master WHERE type='table';"

# 验证DuckDB
python3 << 'EOF'
import duckdb
conn = duckdb.connect('data/market_data.duckdb')
result = conn.execute("SHOW TABLES").fetchall()
print("DuckDB表列表:", result)
conn.close()
EOF

# 验证MySQL
mysql -u your_username -p stock_analysis -e "SHOW TABLES;"
```

## 数据库配置

### 配置文件 (config.yaml)

```yaml
database:
  # 数据库类型: sqlite 或 mysql
  type: sqlite  # 或 mysql
  
  # SQLite配置
  sqlite_path: ./data/stock_analysis.db
  
  # DuckDB配置（始终需要）
  duckdb_path: ./data/market_data.duckdb
  
  # MySQL配置（type=mysql时需要）
  mysql:
    host: localhost
    port: 3306
    database: stock_analysis
    username: your_username
    password: your_password
    pool:
      size: 50
      max_overflow: 10
      timeout: 30
      recycle: 3600
    charset: utf8mb4
    collation: utf8mb4_unicode_ci
```

### 环境变量（推荐用于MySQL）

```bash
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_DATABASE=stock_analysis
export MYSQL_USER=your_username
export MYSQL_PASSWORD=your_password
```

## 数据库用途对比

| 特性 | SQLite | MySQL 8.0 | DuckDB |
|------|--------|-----------|--------|
| **主要用途** | 存储元数据和配置（默认） | 存储元数据和配置（可选） | 存储历史行情数据（必需） |
| **数据量** | 中小规模（MB级别） | 大规模（GB级别） | 大规模（GB级别） |
| **查询类型** | 事务性查询 | 事务性查询 | 分析型查询 |
| **存储方式** | 行式存储 | 行式存储 | 列式存储 |
| **并发支持** | 读写锁 | 连接池+事务 | 并发查询+写入锁 |
| **性能特点** | 快速事务处理 | 高并发、连接池 | OLAP高性能分析 |
| **适用场景** | 开发环境、单机部署 | 生产环境、高并发 | 历史数据分析、回测 |

## 表关系说明

### SQLite数据库表关系

```
stocks (股票基础信息)
    ↓
strategy_results (策略执行结果)
    ↓
strategies (策略配置)

job_logs (定时任务日志)
    ↓
task_execution_details (任务执行详情)

data_update_history (数据更新历史)
system_logs (系统日志)
```

### DuckDB数据库表

```
daily_market (股票日线行情)
    ├── code (股票代码) ─────┐
    ├── trade_date (交易日期) │
    ├── open/high/low/close   │ 关联SQLite的
    ├── volume (成交量)       │ stocks表的code字段
    ├── amount (成交额)       │
    ├── change_pct (涨跌幅)   │
    └── turnover_rate (换手率)┘
```

## 常用操作

### 查询SQLite数据

```python
from app.models import get_sqlite_db

db = get_sqlite_db()

# 查询所有股票
stocks = db.execute_query("SELECT * FROM stocks LIMIT 10")

# 查询启用的策略
strategies = db.execute_query("SELECT * FROM strategies WHERE enabled = 1")
```

### 查询DuckDB数据

```python
from app.models import get_duckdb

duckdb = get_duckdb()

# 查询某股票的最新行情
data = duckdb.execute_query("""
    SELECT * FROM daily_market 
    WHERE code = '000001' 
    ORDER BY trade_date DESC 
    LIMIT 100
""")
```

### 数据导入

```python
# 导入历史行情到DuckDB
import pandas as pd
from app.models import get_duckdb

duckdb = get_duckdb()

# 读取CSV文件
df = pd.read_csv('market_data.csv')

# 插入到DuckDB
duckdb.insert_dataframe('daily_market', df)
```

## 性能优化建议

### SQLite优化

1. 定期清理旧数据
2. 为常用查询字段创建索引
3. 定期执行 VACUUM 命令
4. 使用事务批量操作

### DuckDB优化

1. 使用 WHERE 子句过滤数据
2. 利用列式存储优势，只查询需要的列
3. 使用聚合函数进行统计
4. 定期执行 PRAGMA analyze 更新统计信息

## 备份与恢复

### SQLite备份

```bash
# 备份
cp data/stock_analysis.db data/stock_analysis.db.backup

# 或使用SQLite命令
sqlite3 data/stock_analysis.db ".backup data/stock_analysis.db.backup"
```

### DuckDB备份

```bash
# 直接复制文件
cp data/market_data.duckdb data/market_data.duckdb.backup
```

## 故障排查

### SQLite常见问题

1. **数据库锁定**: 确保没有其他进程占用数据库文件
2. **查询缓慢**: 检查是否缺少索引，使用 EXPLAIN QUERY PLAN 分析查询
3. **数据库损坏**: 使用 `PRAGMA integrity_check` 检查完整性

### DuckDB常见问题

1. **内存不足**: 增加内存限制或使用LIMIT限制返回记录数
2. **查询缓慢**: 使用 WHERE 子句过滤数据，避免全表扫描
3. **文件锁定**: 确保写入操作使用锁机制

## 迁移到MySQL

如果需要从SQLite迁移到MySQL，请参考 [MySQL迁移指南](../mysql-migration-guide.md)。

### 快速迁移命令

```bash
# 1. 安装依赖
pip install pymysql dbutils tqdm

# 2. 配置MySQL连接
# 编辑 config.yaml 或设置环境变量

# 3. 执行迁移
python tools/migrate_sqlite_to_mysql.py

# 4. 验证迁移
python tools/validate_data.py

# 5. 切换到MySQL
# 修改 config.yaml: database.type = mysql

# 6. 重启应用
```

### 回滚到SQLite

如果需要从MySQL回滚到SQLite，请参考 [MySQL回滚指南](../mysql-rollback-guide.md)。

```bash
# 运行回滚工具
python tools/rollback_migration.py
```

## 参考文档

- [SQLite官方文档](https://www.sqlite.org/docs.html)
- [DuckDB官方文档](https://duckdb.org/docs/)

## 更新日志

- **2025-12-27**: 创建数据库文档，包含SQLite和DuckDB的完整Schema说明和建表SQL
