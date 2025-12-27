# SQLite 数据库 Schema 说明

## 数据库概述

- **数据库名称**: `stock_analysis.db`
- **数据库类型**: SQLite
- **用途**: 存储股票基础信息、策略配置、策略执行结果、系统日志等
- **路径**: `./data/stock_analysis.db`

---

## 表结构说明

### 1. stocks（股票基础信息表）

存储A股市场股票的基础信息。

| 字段名 | 数据类型 | 约束 | 说明 |
|--------|---------|------|------|
| code | TEXT | PRIMARY KEY | 股票代码（如：000001） |
| name | TEXT | NOT NULL | 股票名称（如：平安银行） |
| list_date | TEXT | | 上市日期（YYYY-MM-DD） |
| industry | TEXT | | 所属行业（如：银行） |
| market_type | TEXT | | 市场类型（如：主板、创业板） |
| status | TEXT | DEFAULT 'normal' | 股票状态（normal/delisted） |
| created_at | TEXT | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TEXT | DEFAULT CURRENT_TIMESTAMP | 更新时间 |

**索引**: 
- 主键索引：code

---

### 2. strategies（策略配置表）

存储交易策略的配置信息。

| 字段名 | 数据类型 | 约束 | 说明 |
|--------|---------|------|------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 策略ID |
| name | TEXT | NOT NULL UNIQUE | 策略名称 |
| description | TEXT | | 策略描述 |
| config | TEXT | NOT NULL | 策略配置（JSON格式） |
| enabled | INTEGER | DEFAULT 1 | 是否启用（1=启用，0=禁用） |
| created_at | TEXT | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TEXT | DEFAULT CURRENT_TIMESTAMP | 更新时间 |
| last_executed_at | TEXT | | 最后执行时间 |

**索引**: 
- 主键索引：id
- 唯一索引：name

---

### 3. strategy_results（策略执行结果表）

存储策略执行的历史结果。

| 字段名 | 数据类型 | 约束 | 说明 |
|--------|---------|------|------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 结果ID |
| strategy_id | INTEGER | NOT NULL, FOREIGN KEY | 关联的策略ID |
| stock_code | TEXT | NOT NULL, FOREIGN KEY | 股票代码 |
| trigger_date | TEXT | NOT NULL | 触发日期 |
| trigger_price | REAL | | 触发价格 |
| rise_percent | REAL | | 涨跌幅 |
| result_data | TEXT | | 结果详情（JSON格式） |
| executed_at | TEXT | DEFAULT CURRENT_TIMESTAMP | 执行时间 |

**索引**:
- 主键索引：id
- `idx_strategy_results_strategy_id`: strategy_id
- `idx_strategy_results_executed_at`: executed_at

**外键关系**:
- strategy_id → strategies(id) ON DELETE CASCADE
- stock_code → stocks(code)

---

### 4. system_logs（系统日志表）

存储系统运行日志。

| 字段名 | 数据类型 | 约束 | 说明 |
|--------|---------|------|------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 日志ID |
| timestamp | TEXT | DEFAULT CURRENT_TIMESTAMP | 时间戳 |
| level | TEXT | NOT NULL | 日志级别（DEBUG/INFO/WARNING/ERROR） |
| module | TEXT | NOT NULL | 模块名称 |
| message | TEXT | NOT NULL | 日志消息 |
| details | TEXT | | 详细信息 |

**索引**:
- 主键索引：id
- `idx_system_logs_timestamp`: timestamp
- `idx_system_logs_level`: level

---

### 5. data_update_history（数据更新历史表）

记录数据导入和更新的历史。

| 字段名 | 数据类型 | 约束 | 说明 |
|--------|---------|------|------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 更新ID |
| update_type | TEXT | NOT NULL | 更新类型（如：stock_list/daily_market） |
| start_time | TEXT | NOT NULL | 开始时间 |
| end_time | TEXT | | 结束时间 |
| total_count | INTEGER | DEFAULT 0 | 总数量 |
| success_count | INTEGER | DEFAULT 0 | 成功数量 |
| fail_count | INTEGER | DEFAULT 0 | 失败数量 |
| status | TEXT | DEFAULT 'running' | 状态（running/completed/failed） |
| error_message | TEXT | | 错误信息 |

**索引**: 
- 主键索引：id

---

### 6. job_logs（定时任务执行日志表）

记录定时任务的执行情况。

| 字段名 | 数据类型 | 约束 | 说明 |
|--------|---------|------|------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 日志ID |
| job_type | TEXT | NOT NULL | 任务类型 |
| job_name | TEXT | NOT NULL | 任务名称 |
| status | TEXT | NOT NULL | 执行状态（success/failed/running） |
| started_at | TEXT | NOT NULL | 开始时间 |
| completed_at | TEXT | | 完成时间 |
| duration | REAL | | 执行时长（秒） |
| message | TEXT | | 执行消息 |
| error | TEXT | | 错误信息 |

**索引**:
- 主键索引：id
- `idx_job_logs_job_type`: job_type
- `idx_job_logs_started_at`: started_at

---

### 7. task_execution_details（任务执行详细结果表）

记录任务执行的详细结果信息。

| 字段名 | 数据类型 | 约束 | 说明 |
|--------|---------|------|------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 详情ID |
| job_log_id | INTEGER | NOT NULL, FOREIGN KEY | 关联的任务日志ID |
| task_type | TEXT | NOT NULL | 任务类型 |
| stock_code | TEXT | | 股票代码 |
| stock_name | TEXT | | 股票名称 |
| detail_type | TEXT | NOT NULL | 详情类型 |
| detail_data | TEXT | NOT NULL | 详情数据（JSON格式） |
| created_at | TEXT | DEFAULT CURRENT_TIMESTAMP | 创建时间 |

**索引**:
- 主键索引：id
- `idx_task_execution_details_job_log_id`: job_log_id
- `idx_task_execution_details_task_type`: task_type
- `idx_task_execution_details_stock_code`: stock_code

**外键关系**:
- job_log_id → job_logs(id) ON DELETE CASCADE

---

## 数据库关系图

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

---

## 使用场景

1. **stocks**: 存储所有A股股票的基本信息，用于股票列表展示和查询
2. **strategies**: 存储交易策略的配置，支持策略的创建、修改和启用/禁用
3. **strategy_results**: 记录策略执行的历史结果，用于回测和策略分析
4. **system_logs**: 存储系统运行日志，用于问题排查和系统监控
5. **data_update_history**: 跟踪数据导入历史，了解数据更新情况
6. **job_logs**: 记录定时任务执行情况，用于任务调度监控
7. **task_execution_details**: 存储任务执行的详细结果，用于深入分析

---

## 性能优化建议

1. 定期清理旧的 system_logs 和 strategy_results 数据，避免数据库膨胀
2. 对 strategy_results 的 executed_at 字段建立索引，支持按时间范围查询
3. 对 job_logs 的 started_at 字段建立索引，支持按时间排序
4. 定期执行 VACUUM 命令优化数据库空间
5. 考虑对大表进行分区（如按时间分区 strategy_results）

---

## 数据完整性约束

1. **外键约束**: strategy_results 和 task_execution_details 表都有外键约束，确保数据引用完整性
2. **级联删除**: 删除 strategies 时会自动关联删除 strategy_results，删除 job_logs 时会自动删除 task_execution_details
3. **唯一约束**: strategies 表的 name 字段有唯一约束，防止重复策略名称
4. **非空约束**: 关键字段设置了 NOT NULL 约束，确保数据完整性
