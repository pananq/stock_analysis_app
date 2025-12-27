# 任务执行详细结果记录功能

## 功能概述

系统现在支持记录每次任务执行的详细结果，包括：
- **数据导入任务**：记录每只股票的导入结果（成功/失败）、记录数、日期范围等
- **策略执行任务**：记录每只匹配股票的详细信息、触发日期、涨幅等

## 数据库设计

### task_execution_details 表

用于存储任务执行的详细结果：

```sql
CREATE TABLE task_execution_details (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_log_id INTEGER NOT NULL,           -- 关联的任务日志ID
    task_type TEXT NOT NULL,               -- 任务类型（data_import, strategy_execution等）
    stock_code TEXT,                       -- 股票代码（可选）
    stock_name TEXT,                       -- 股票名称（可选）
    detail_type TEXT NOT NULL,             -- 详细类型（stock_import_success, strategy_match等）
    detail_data TEXT NOT NULL,             -- 详细数据（JSON格式）
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_log_id) REFERENCES job_logs(id) ON DELETE CASCADE
);
```

## 详细类型说明

### 数据导入任务

- **stock_import_success**: 股票导入成功
  - `records`: 导入的记录数
  - `start_date`: 开始日期
  - `end_date`: 结束日期

- **stock_import_failed**: 股票导入失败
  - `records`: 0
  - `start_date`: 开始日期
  - `end_date`: 结束日期
  - `error`: 错误信息

### 增量更新任务

- **stock_update_success**: 股票更新成功
  - `records`: 更新的记录数
  - `start_date`: 开始日期
  - `end_date`: 结束日期

- **stock_update_failed**: 股票更新失败
  - `records`: 0
  - `start_date`: 开始日期
  - `end_date`: 结束日期
  - `error`: 错误信息

### 策略执行任务

- **strategy_match**: 策略匹配成功
  - `trigger_date`: 触发日期
  - `trigger_pct_change`: 触发涨幅
  - `observation_days`: 观察天数
  - `ma_period`: 均线周期
  - `observation_result`: 观察结果详情

## API接口

### 获取任务执行详细结果

```http
GET /api/data/job-logs/{job_log_id}/details
```

**Query参数**:
- `limit`: 返回记录数（默认1000）
- `offset`: 偏移量（默认0）
- `detail_type`: 详细类型过滤（可选）

**响应示例**:
```json
{
  "success": true,
  "data": {
    "job_log": {
      "id": 123,
      "job_type": "data_import",
      "job_name": "全量数据导入",
      "status": "success",
      "started_at": "2025-12-27 10:00:00 GMT",
      "completed_at": "2025-12-27 12:30:00 GMT",
      "duration": 9000.5,
      "message": "成功: 4500, 失败: 10, 总记录: 1125000"
    },
    "details": [
      {
        "id": 1,
        "job_log_id": 123,
        "task_type": "data_import",
        "stock_code": "000001",
        "stock_name": "平安银行",
        "detail_type": "stock_import_success",
        "detail_data": {
          "records": 250,
          "start_date": "2022-01-01",
          "end_date": "2025-12-27"
        },
        "created_at": "2025-12-27 10:05:23 GMT"
      }
    ],
    "summary": {
      "stock_import_success": 4500,
      "stock_import_failed": 10
    },
    "pagination": {
      "limit": 1000,
      "offset": 0,
      "total": 4510
    }
  }
}
```

## 使用方法

### 在仪表盘查看任务详情

1. 访问仪表盘页面 `http://localhost:8000/`
2. 在"最近任务执行"部分，找到要查看的任务
3. 点击"查看详情"按钮
4. 在弹出的模态框中查看：
   - 任务基本信息（名称、状态、耗时等）
   - 执行统计（成功数、失败数等）
   - 详细记录列表（每只股票的执行结果）

### 通过API查询

```python
import requests

# 获取任务详情
job_log_id = 123
response = requests.get(f'http://localhost:5000/api/data/job-logs/{job_log_id}/details')
data = response.json()

# 查看任务信息
job_log = data['data']['job_log']
print(f"任务名称: {job_log['job_name']}")
print(f"状态: {job_log['status']}")
print(f"耗时: {job_log['duration']}秒")

# 查看详细记录
details = data['data']['details']
for detail in details:
    print(f"{detail['stock_code']} - {detail['stock_name']}: {detail['detail_type']}")
    print(f"  详细数据: {detail['detail_data']}")

# 查看统计摘要
summary = data['data']['summary']
print(f"统计摘要: {summary}")
```

## 示例场景

### 场景1：查看数据导入结果

执行全量数据导入后，可以查看：
- 哪些股票导入成功，导入了多少条记录
- 哪些股票导入失败，失败原因是什么
- 每只股票的数据日期范围

### 场景2：查看策略执行结果

执行策略后，可以查看：
- 哪些股票匹配了策略条件
- 每只股票的触发日期和涨幅
- 观察期内的表现情况

### 场景3：问题排查

当任务执行失败时，可以通过详细记录：
- 定位具体是哪只股票导致的问题
- 查看错误信息
- 分析失败原因

## 性能考虑

- 详细记录会占用额外的数据库空间
- 建议定期清理旧的任务日志和详细记录
- 对于大批量导入（如5000只股票），详细记录可能达到数千条
- 查询时使用分页参数避免一次性加载过多数据

## 未来优化方向

1. **数据清理策略**：自动清理超过N天的任务详细记录
2. **导出功能**：支持将任务详细结果导出为Excel或CSV
3. **统计分析**：提供更丰富的统计图表
4. **实时通知**：任务完成后发送邮件或消息通知
5. **失败重试**：对失败的股票支持单独重试