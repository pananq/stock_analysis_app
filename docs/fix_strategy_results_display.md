# 策略执行结果显示问题修复总结

## 问题描述

用户反馈：策略执行成功后，执行结果（匹配策略的股票，以及匹配时间）在任务详情页面没有呈现。

**截图显示：**
- 任务状态：成功
- 消息：成功: 639, 扫描: 3848
- 详细记录：共0条

---

## 问题分析

通过排查，发现了以下问题：

### 1. 数据库表结构不匹配

`strategy_results` 表的实际结构与代码期望的列名不一致：

**实际表结构：**
```sql
CREATE TABLE strategy_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_id INTEGER NOT NULL,
    stock_code TEXT NOT NULL,
    trigger_date TEXT NOT NULL,
    trigger_price REAL,
    rise_percent REAL,
    result_data TEXT,
    executed_at TEXT DEFAULT CURRENT_TIMESTAMP
)
```

**代码期望的表结构：**
```sql
CREATE TABLE strategy_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_id INTEGER NOT NULL,
    stock_code TEXT NOT NULL,
    stock_name TEXT,                    -- 缺失
    trigger_date TEXT NOT NULL,
    trigger_pct_change REAL,            -- 缺失
    observation_days INTEGER,           -- 缺失
    ma_period INTEGER,                  -- 缺失
    observation_result TEXT,            -- 缺失
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
```

### 2. Decimal 类型序列化失败

日志显示错误：
```
保存执行结果失败: Object of type Decimal is not JSON serializable
保存执行结果: 0 条
```

这是因为 DuckDB 查询返回的数据包含 `Decimal` 类型，而 Python 的 `json.dumps()` 默认不支持序列化 `Decimal` 类型。

---

## 解决方案

### 1. 更新数据库表结构

执行 SQL 脚本更新 `strategy_results` 表结构：

```sql
-- 备份现有数据
CREATE TABLE IF NOT EXISTS strategy_results_backup AS SELECT * FROM strategy_results;

-- 删除旧表
DROP TABLE IF EXISTS strategy_results;

-- 创建新表
CREATE TABLE IF NOT EXISTS strategy_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_id INTEGER NOT NULL,
    stock_code TEXT NOT NULL,
    stock_name TEXT,
    trigger_date TEXT NOT NULL,
    trigger_pct_change REAL,
    observation_days INTEGER,
    ma_period INTEGER,
    observation_result TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (strategy_id) REFERENCES strategies(id) ON DELETE CASCADE,
    FOREIGN KEY (stock_code) REFERENCES stocks(code)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_strategy_results_strategy_id 
ON strategy_results(strategy_id);

CREATE INDEX IF NOT EXISTS idx_strategy_results_executed_at 
ON strategy_results(created_at);
```

### 2. 添加 Decimal 类型转换函数

在 `strategy_routes.py` 中添加 `convert_decimal` 函数：

```python
from decimal import Decimal

def convert_decimal(obj):
    """转换Decimal为float以便JSON序列化"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: convert_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimal(v) for v in obj]
    return obj
```

### 3. 修复 _save_results 方法

在 `strategy_executor.py` 的 `_save_results` 方法中添加 Decimal 转换：

```python
from decimal import Decimal

def convert_decimal(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: convert_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimal(v) for v in obj]
    return obj

# 在保存前转换Decimal
observation_result = convert_decimal(match['observation_result'])
```

### 4. 在记录任务详情时使用转换函数

在 `strategy_routes.py` 的 `execute_with_logging` 函数中使用 `convert_decimal`：

```python
# 转换Decimal类型
detail_data = {
    'trigger_date': match.get('trigger_date'),
    'trigger_pct_change': convert_decimal(match.get('trigger_pct_change')),
    'observation_days': match.get('observation_days'),
    'ma_period': match.get('ma_period'),
    'observation_result': convert_decimal(match.get('observation_result'))
}

scheduler.log_task_detail(
    job_log_id=job_log_id,
    task_type='strategy_execution',
    detail_type='strategy_match',
    stock_code=match.get('stock_code'),
    stock_name=match.get('stock_name'),
    detail_data=detail_data
)
```

### 5. 添加调试日志

在 `strategy_routes.py` 和 `task_scheduler.py` 中添加详细的调试日志，便于追踪问题：

```python
logger.info(f"任务开始记录: job_log_id={job_log_id}")
logger.info(f"开始记录{len(result['matches'])}个匹配的股票详情到task_execution_details表")
logger.info(f"成功记录{saved_details}条股票详情")
```

---

## 测试验证

创建测试脚本验证修复效果：

```python
# 测试Decimal转换
match_data = {
    'stock_code': '000001',
    'stock_name': '平安银行',
    'trigger_date': '2025-12-27',
    'trigger_pct_change': Decimal('5.5'),
    'observation_result': {
        'close': Decimal('10.8'),
        'ma5': Decimal('10.2')
    }
}

# 转换并保存
converted_data = convert_decimal(match_data)
scheduler.log_task_detail(
    job_log_id=job_log_id,
    task_type='strategy_execution',
    detail_type='strategy_match',
    stock_code=converted_data['stock_code'],
    stock_name=converted_data['stock_name'],
    detail_data=converted_data
)
```

**测试结果：** ✅ 所有测试通过

---

## 修复的文件

1. `app/models/sqlite_db.py` - 数据库表结构（已通过 SQL 脚本更新）
2. `app/services/strategy_executor.py` - 修复 `_save_results` 方法
3. `app/api/routes/strategy_routes.py` - 添加 `convert_decimal` 函数和调试日志
4. `app/scheduler/task_scheduler.py` - 添加 `log_task_detail` 方法的调试日志

---

## 使用说明

### 验证修复

1. 执行策略（如"大涨后站稳5日线"）
2. 在仪表盘的"最近任务执行"中找到该任务
3. 点击"查看详情"按钮
4. 查看详细记录，应该能看到：
   - 任务信息（名称、状态、耗时等）
   - 执行统计（成功数、扫描数等）
   - 详细记录（每只匹配股票的代码、名称、触发日期、涨幅等）

### 预期效果

**任务详情页面应该显示：**
```
任务信息:
- 任务名称: 执行策略: 大涨后站稳5日线
- 状态: 成功
- 耗时: 3765.6秒
- 消息: 成功: 639, 扫描: 3848

执行统计:
- strategy_match: 639

详细记录 (共639条):
股票代码 | 股票名称 | 类型 | 详细信息 | 时间
000001  | 平安银行  | strategy_match | 触发日期: 2025-12-27, 涨幅: 5.5% | 2025-12-27 14:07:45
000002  | 万科A    | strategy_match | 触发日期: 2025-12-26, 涨幅: 6.2% | 2025-12-27 14:07:45
...
```

---

## 技术要点

### Decimal 类型处理

DuckDB 和 SQLite 在处理浮点数时会使用 `Decimal` 类型以保证精度。但在 JSON 序列化时需要转换为 `float` 类型。

**最佳实践：**
- 从数据库读取数据后立即转换 Decimal
- 在保存到数据库前确保数据类型正确
- 使用辅助函数统一处理转换逻辑

### 数据库表结构维护

**建议：**
- 使用数据库迁移工具（如 Alembic）管理表结构变更
- 在代码中定义表结构模型，保持与实际数据库一致
- 定期同步文档中的表结构说明

### 调试日志

**建议：**
- 在关键步骤添加日志记录
- 记录重要参数和返回值
- 使用适当的日志级别（INFO、DEBUG、ERROR）

---

## 后续优化建议

1. **数据库迁移工具**：引入 Alembic 等数据库迁移工具，统一管理表结构变更
2. **类型转换工具**：创建统一的类型转换工具类，处理各种数据类型的序列化
3. **单元测试**：为核心功能添加单元测试，确保代码质量
4. **日志优化**：完善日志系统，添加更多调试信息
5. **错误处理**：增强错误处理机制，提供更友好的错误提示

---

## 修复日期

2025-12-27

---

## 相关文档

- [任务执行详细结果功能文档](./task_execution_details.md)
- [SQLite 数据库 Schema 说明](./database/sqlite_schema.md)
- [API 文档](./API.md)
