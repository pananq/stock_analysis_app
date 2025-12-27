# MySQL 数据库 Schema 文档

## 概述

本文档描述了股票分析系统 MySQL 8.0 数据库的表结构和字段定义。

## 数据库配置

- **数据库类型**: MySQL 8.0+
- **字符集**: utf8mb4
- **排序规则**: utf8mb4_unicode_ci
- **存储引擎**: InnoDB
- **时区**: 根据应用配置（默认 Asia/Shanghai）

## 数据表

### 1. stocks (股票基础信息表)

存储股票的基础信息，包括股票代码、名称、上市日期、行业分类等。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| code | VARCHAR(20) | PRIMARY KEY | 股票代码，唯一标识 |
| name | VARCHAR(500) | NOT NULL | 股票名称 |
| list_date | DATE | | 上市日期 |
| industry | VARCHAR(200) | INDEX | 所属行业 |
| market_type | VARCHAR(50) | INDEX | 市场类型（主板、创业板等） |
| status | VARCHAR(50) | DEFAULT 'normal', INDEX | 股票状态 |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DATETIME | ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

**索引**:
- PRIMARY KEY (code)
- INDEX idx_status (status)
- INDEX idx_industry (industry)
- INDEX idx_market_type (market_type)

---

### 2. strategies (策略配置表)

存储股票分析策略的配置信息。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INT | AUTO_INCREMENT, PRIMARY KEY | 策略ID，自增主键 |
| name | VARCHAR(500) | UNIQUE, NOT NULL | 策略名称，唯一 |
| description | TEXT | | 策略描述 |
| config | TEXT | NOT NULL | 策略配置（JSON格式） |
| enabled | TINYINT(1) | DEFAULT 1, INDEX | 是否启用（0/1） |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DATETIME | ON UPDATE CURRENT_TIMESTAMP | 更新时间 |
| last_executed_at | DATETIME | | 最后执行时间 |

**索引**:
- PRIMARY KEY (id)
- UNIQUE INDEX idx_name (name)
- INDEX idx_enabled (enabled)

---

### 3. strategy_results (策略执行结果表)

存储策略执行的结果数据。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INT | AUTO_INCREMENT, PRIMARY KEY | 结果ID，自增主键 |
| strategy_id | INT | NOT NULL, FOREIGN KEY | 关联的策略ID |
| stock_code | VARCHAR(20) | NOT NULL, FOREIGN KEY | 股票代码 |
| trigger_date | DATE | NOT NULL, INDEX | 触发日期 |
| trigger_price | DECIMAL(10,4) | | 触发价格 |
| rise_percent | DECIMAL(10,4) | | 涨幅百分比 |
| result_data | TEXT | | 结果详情数据（JSON格式） |
| executed_at | DATETIME | DEFAULT CURRENT_TIMESTAMP, INDEX | 执行时间 |

**外键**:
- FOREIGN KEY (strategy_id) REFERENCES strategies(id) ON DELETE CASCADE
- FOREIGN KEY (stock_code) REFERENCES stocks(code) ON DELETE CASCADE

**索引**:
- PRIMARY KEY (id)
- INDEX idx_strategy_id (strategy_id)
- INDEX idx_stock_code (stock_code)
- INDEX idx_trigger_date (trigger_date)
- INDEX idx_executed_at (executed_at)

---

### 4. system_logs (系统日志表)

存储系统运行日志信息。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INT | AUTO_INCREMENT, PRIMARY KEY | 日志ID，自增主键 |
| timestamp | DATETIME | DEFAULT CURRENT_TIMESTAMP, INDEX | 时间戳 |
| level | VARCHAR(50) | NOT NULL, INDEX | 日志级别（DEBUG/INFO/WARNING/ERROR/CRITICAL） |
| module | VARCHAR(200) | NOT NULL, INDEX | 模块名称 |
| message | TEXT | NOT NULL | 日志消息 |
| details | TEXT | | 详细信息 |

**索引**:
- PRIMARY KEY (id)
- INDEX idx_timestamp (timestamp)
- INDEX idx_level (level)
- INDEX idx_module (module)

---

### 5. data_update_history (数据更新历史表)

记录数据更新的历史信息。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INT | AUTO_INCREMENT, PRIMARY KEY | 历史记录ID，自增主键 |
| update_type | VARCHAR(100) | NOT NULL, INDEX | 更新类型 |
| start_time | DATETIME | NOT NULL, INDEX | 开始时间 |
| end_time | DATETIME | | 结束时间 |
| total_count | INT | DEFAULT 0 | 总记录数 |
| success_count | INT | DEFAULT 0 | 成功记录数 |
| fail_count | INT | DEFAULT 0 | 失败记录数 |
| status | VARCHAR(50) | DEFAULT 'running', INDEX | 状态 |
| error_message | TEXT | | 错误消息 |

**索引**:
- PRIMARY KEY (id)
- INDEX idx_update_type (update_type)
- INDEX idx_status (status)
- INDEX idx_start_time (start_time)

---

### 6. job_logs (定时任务执行日志表)

记录定时任务的执行情况。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INT | AUTO_INCREMENT, PRIMARY KEY | 日志ID，自增主键 |
| job_type | VARCHAR(100) | NOT NULL, INDEX | 任务类型 |
| job_name | VARCHAR(200) | NOT NULL | 任务名称 |
| status | VARCHAR(50) | NOT NULL, INDEX | 执行状态 |
| started_at | DATETIME | NOT NULL, INDEX | 开始时间 |
| completed_at | DATETIME | | 完成时间 |
| duration | DECIMAL(10,4) | | 执行时长（秒） |
| message | TEXT | | 消息 |
| error | TEXT | | 错误信息 |

**索引**:
- PRIMARY KEY (id)
- INDEX idx_job_type (job_type)
- INDEX idx_status (status)
- INDEX idx_started_at (started_at)

---

### 7. task_execution_details (任务执行详情表)

记录任务执行的详细结果。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INT | AUTO_INCREMENT, PRIMARY KEY | 详情ID，自增主键 |
| job_log_id | INT | NOT NULL, FOREIGN KEY | 关联的任务日志ID |
| task_type | VARCHAR(100) | NOT NULL, INDEX | 任务类型 |
| stock_code | VARCHAR(20) | INDEX | 股票代码 |
| stock_name | VARCHAR(500) | | 股票名称 |
| detail_type | VARCHAR(100) | NOT NULL, INDEX | 详情类型 |
| detail_data | TEXT | NOT NULL | 详情数据 |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP | 创建时间 |

**外键**:
- FOREIGN KEY (job_log_id) REFERENCES job_logs(id) ON DELETE CASCADE

**索引**:
- PRIMARY KEY (id)
- INDEX idx_job_log_id (job_log_id)
- INDEX idx_task_type (task_type)
- INDEX idx_stock_code (stock_code)
- INDEX idx_detail_type (detail_type)

---

## 数据类型映射

| SQLite 类型 | MySQL 类型 | 说明 |
|-------------|------------|------|
| TEXT (主键) | VARCHAR(20) | 短文本，如股票代码 |
| TEXT (普通) | VARCHAR(500) | 中等长度文本 |
| TEXT (JSON) | TEXT | JSON数据 |
| INTEGER | INT | 整数 |
| REAL | DECIMAL(10,4) | 浮点数，保留4位小数 |
| INTEGER (布尔) | TINYINT(1) | 布尔值（0/1） |
| TEXT (日期) | DATE | 日期 |
| TEXT (时间) | DATETIME | 日期时间 |

---

## 表关系图

```mermaid
erDiagram
    stocks ||--o{ strategy_results : "被引用"
    strategies ||--o{ strategy_results : "产生"
    job_logs ||--o{ task_execution_details : "包含"
    
    stocks {
        VARCHAR(20) code PK
        VARCHAR(500) name
        DATE list_date
        VARCHAR(200) industry
        VARCHAR(50) market_type
        VARCHAR(50) status
    }
    
    strategies {
        INT id PK
        VARCHAR(500) name UK
        TEXT description
        TEXT config
        TINYINT(1) enabled
    }
    
    strategy_results {
        INT id PK
        INT strategy_id FK
        VARCHAR(20) stock_code FK
        DATE trigger_date
        DECIMAL(10,4) trigger_price
        DECIMAL(10,4) rise_percent
        TEXT result_data
    }
    
    system_logs {
        INT id PK
        DATETIME timestamp
        VARCHAR(50) level
        VARCHAR(200) module
        TEXT message
    }
    
    data_update_history {
        INT id PK
        VARCHAR(100) update_type
        DATETIME start_time
        DATETIME end_time
        INT total_count
    }
    
    job_logs {
        INT id PK
        VARCHAR(100) job_type
        VARCHAR(200) job_name
        VARCHAR(50) status
        DATETIME started_at
        DECIMAL(10,4) duration
    }
    
    task_execution_details {
        INT id PK
        INT job_log_id FK
        VARCHAR(100) task_type
        VARCHAR(20) stock_code
        TEXT detail_data
    }
```

---

## 性能优化建议

### 1. 索引优化

- 所有外键字段都已创建索引
- 常用查询条件字段已创建索引
- 时间字段已创建索引用于范围查询

### 2. 查询优化

- 避免使用 `SELECT *`，只查询需要的字段
- 使用分页查询避免一次性加载大量数据
- 合理使用索引，避免全表扫描

### 3. 连接池配置

建议配置：
- 连接池大小: 50
- 最大空闲连接: 10
- 连接超时: 30秒
- 连接回收时间: 3600秒

---

## 维护建议

### 1. 定期备份

建议每天备份一次数据库：
```bash
mysqldump -u username -p database_name > backup_$(date +%Y%m%d).sql
```

### 2. 日志清理

定期清理旧的系统日志：
```sql
DELETE FROM system_logs WHERE timestamp < DATE_SUB(NOW(), INTERVAL 3 MONTH);
```

### 3. 索引优化

定期分析表并优化索引：
```sql
ANALYZE TABLE stocks;
OPTIMIZE TABLE stocks;
```

### 4. 监控慢查询

启用慢查询日志，监控执行时间超过阈值的查询。

---

## 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.0 | 2025-12-27 | 初始版本，从SQLite迁移到MySQL |
