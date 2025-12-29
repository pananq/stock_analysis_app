# SQLite 到 MySQL 8.0 数据库迁移指南

## 目录

- [概述](#概述)
- [前置准备](#前置准备)
- [迁移流程](#迁移流程)
- [验证迁移](#验证迁移)
- [常见问题](#常见问题)
- [性能优化](#性能优化)

---

## 概述

本文档提供了将股海罗盘从 SQLite 数据库迁移到 MySQL 8.0 数据库的完整指南。

### 迁移范围

迁移包含以下 7 个数据表：

1. **stocks** - 股票基础信息（约 5000+ 条记录）
2. **strategies** - 策略配置（约 5-10 条记录）
3. **strategy_results** - 策略执行结果（可能有数万条记录）
4. **system_logs** - 系统日志（可能有数万条记录）
5. **data_update_history** - 数据更新历史（约数十条记录）
6. **job_logs** - 定时任务日志（可能有数百条记录）
7. **task_execution_details** - 任务执行详情（可能有数万条记录）

### 数据类型映射

| SQLite 类型 | MySQL 8.0 类型 |
|-------------|----------------|
| TEXT (主键) | VARCHAR(20) |
| TEXT (普通) | VARCHAR(500) |
| TEXT (JSON) | TEXT |
| INTEGER | INT |
| REAL | DECIMAL(10,4) |
| INTEGER (布尔) | TINYINT(1) |
| TEXT (日期) | DATE |
| TEXT (时间) | DATETIME |

---

## 前置准备

### 1. 安装 MySQL 8.0

确保已安装 MySQL 8.0 或更高版本：

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install mysql-server

# CentOS/RHEL
sudo yum install mysql-server

# macOS
brew install mysql
```

### 2. 创建数据库和用户

```sql
-- 登录 MySQL
mysql -u root -p

-- 创建数据库
CREATE DATABASE stock_analysis DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 创建用户并授权
CREATE USER 'stock_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON stock_analysis.* TO 'stock_user'@'localhost';
FLUSH PRIVILEGES;
```

### 3. 安装 Python 依赖

安装迁移工具所需的 Python 包：

```bash
# 进入项目目录
cd /path/to/stock-analysis-app

# 安装依赖
pip install pymysql dbutils tqdm
```

### 4. 配置 MySQL 连接参数

编辑 `config.yaml` 文件，配置 MySQL 连接参数：

```yaml
database:
  type: mysql  # 将数据库类型改为 mysql
  
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

或者使用环境变量（推荐）：

```bash
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_DATABASE=stock_analysis
export MYSQL_USER=stock_user
export MYSQL_PASSWORD=your_password
```

---

## 迁移流程

### 步骤 1: 备份 SQLite 数据库

在迁移前，务必备份 SQLite 数据库文件：

```bash
# 创建备份目录
mkdir -p ./data/backups

# 备份 SQLite 数据库
cp ./data/stock_analysis.db ./data/backups/stock_analysis_backup_$(date +%Y%m%d_%H%M%S).db
```

### 步骤 2: 备份配置文件

```bash
cp ./config.yaml ./data/backups/config_backup_$(date +%Y%m%d_%H%M%S).yaml
```

### 步骤 3: 执行数据迁移

运行迁移工具：

```bash
python tools/migrate_sqlite_to_mysql.py
```

迁移工具会：
1. 检查 MySQL 连接
2. 检查 MySQL 表状态
3. 按照正确的顺序迁移数据（考虑外键依赖）
4. 显示实时进度
5. 记录迁移统计信息

#### 迁移参数

```bash
# 覆盖已有数据
python tools/migrate_sqlite_to_mysql.py --overwrite

# 指定 SQLite 数据库路径
python tools/migrate_sqlite_to_mysql.py --sqlite-path /path/to/database.db
```

### 步骤 4: 验证迁移结果

运行数据验证工具：

```bash
python tools/validate_data.py
```

验证工具会：
1. 对比 SQLite 和 MySQL 的记录数
2. 抽样验证数据内容
3. 生成验证报告

#### 验证参数

```bash
# 指定 SQLite 数据库路径
python tools/validate_data.py --sqlite-path /path/to/database.db

# 指定验证报告输出路径
python tools/validate_data.py --report /path/to/report.json
```

### 步骤 5: 切换到 MySQL

确认迁移成功后，修改配置文件中的数据库类型：

```yaml
database:
  type: mysql
```

或使用 `switch_database` 函数：

```python
from app.models.database_factory import switch_database

switch_database('mysql')
```

### 步骤 6: 重启应用

重启应用以使配置生效：

```bash
# 停止应用（如果正在运行）
# 根据实际部署方式执行

# 启动应用
python main.py
```

---

## 验证迁移

### 验证项目

1. **记录数对比**
   - 检查每个表的记录数是否一致

2. **数据抽样验证**
   - 随机抽取数据对比内容是否一致

3. **功能验证**
   - 测试应用的核心功能是否正常
   - 确认股票列表可以正常显示
   - 确认策略配置可以正常查看和修改
   - 确认策略执行结果可以正常显示

### 验证命令

```sql
-- 查看各表记录数
SELECT 
    'stocks' as table_name, COUNT(*) as count FROM stocks
UNION ALL
SELECT 
    'strategies', COUNT(*) FROM strategies
UNION ALL
SELECT 
    'strategy_results', COUNT(*) FROM strategy_results
UNION ALL
SELECT 
    'system_logs', COUNT(*) FROM system_logs
UNION ALL
SELECT 
    'data_update_history', COUNT(*) FROM data_update_history
UNION ALL
SELECT 
    'job_logs', COUNT(*) FROM job_logs
UNION ALL
SELECT 
    'task_execution_details', COUNT(*) FROM task_execution_details;
```

---

## 常见问题

### 问题 1: 连接 MySQL 失败

**错误信息**: `Can't connect to MySQL server`

**解决方案**:
- 检查 MySQL 服务是否运行
- 检查主机地址和端口是否正确
- 检查防火墙设置
- 确认用户权限是否正确

### 问题 2: 字符编码问题

**错误信息**: `Incorrect string value`

**解决方案**:
- 确保数据库使用 `utf8mb4` 字符集
- 确保表和字段使用 `utf8mb4` 排序规则
- 检查配置文件中的字符集设置

### 问题 3: 外键约束错误

**错误信息**: `Cannot add or update a child row`

**解决方案**:
- 检查迁移顺序是否正确
- 确保父表数据已先迁移
- 检查外键关系是否正确

### 问题 4: 时间格式错误

**错误信息**: `Incorrect datetime value`

**解决方案**:
- 迁移工具会自动转换时间格式
- 如果仍有问题，检查 SQLite 中的时间字段格式

### 问题 5: 权限不足

**错误信息**: `Access denied for user`

**解决方案**:
- 确认用户名和密码正确
- 确认用户有足够的权限
- 重新授权：`GRANT ALL PRIVILEGES ON stock_analysis.* TO 'user'@'host';`

---

## 性能优化

### 1. 批量插入优化

迁移工具使用批量插入（每批 1000 条）以提高性能。如需调整：

```python
# 在 migrate_sqlite_to_mysql.py 中修改
batch_size = 1000  # 可以调整为 500-2000
```

### 2. 连接池配置

根据实际负载调整连接池大小：

```yaml
mysql:
  pool:
    size: 50          # 连接池大小
    max_overflow: 10  # 最大额外连接数
    timeout: 30       # 连接超时（秒）
    recycle: 3600     # 连接回收时间（秒）
```

### 3. 索引优化

确保所有常用查询字段都有索引：

```sql
-- 查看索引
SHOW INDEX FROM table_name;

-- 添加索引
CREATE INDEX idx_column_name ON table_name(column_name);
```

### 4. 查询优化

避免全表扫描，使用 EXPLAIN 分析查询：

```sql
EXPLAIN SELECT * FROM stocks WHERE code = '000001';
```

---

## 回滚

如果迁移失败或需要回滚到 SQLite，请参考 [回滚指南](mysql-rollback-guide.md)。

### 快速回滚命令

```bash
# 运行回滚工具
python tools/rollback_migration.py

# 清空 MySQL 数据
python tools/rollback_migration.py --clear-mysql

# 仅生成恢复指南
python tools/rollback_migration.py --guide-only
```

---

## 迁移时间估算

根据数据量估算迁移时间：

| 数据量 | 预估时间 |
|--------|----------|
| < 10,000 条 | < 1 分钟 |
| 10,000 - 50,000 条 | 1-3 分钟 |
| 50,000 - 100,000 条 | 3-5 分钟 |
| > 100,000 条 | 5-10 分钟 |

实际时间取决于：
- 网络速度
- MySQL 服务器性能
- 数据复杂度

---

## 技术支持

如遇到问题，请：

1. 查看应用日志文件
2. 查看迁移验证报告
3. 查看本文档的常见问题部分
4. 联系技术支持

---

## 附录

### A. 迁移工具位置

```
tools/
├── migrate_sqlite_to_mysql.py  # 迁移工具
├── validate_data.py            # 验证工具
└── rollback_migration.py       # 回滚工具
```

### B. 文档位置

```
docs/database/
├── mysql_schema.md            # MySQL Schema 文档
├── mysql_create_tables.sql    # MySQL 建表 SQL
├── mysql-migration-guide.md   # 本文档
└── mysql-rollback-guide.md    # 回滚指南
```

### C. 相关链接

- [MySQL 8.0 官方文档](https://dev.mysql.com/doc/refman/8.0/en/)
- [PyMySQL 文档](https://pymysql.readthedocs.io/)
- [Python 数据库迁移最佳实践](https://docs.python.org/3/library/sqlite3.html)
