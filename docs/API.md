# API接口文档

## 基础信息

- **基础URL**: `http://localhost:5000`
- **数据格式**: JSON
- **字符编码**: UTF-8

## 通用响应格式

### 成功响应
```json
{
  "success": true,
  "data": { ... },
  "message": "操作成功"
}
```

### 失败响应
```json
{
  "success": false,
  "error": "错误信息"
}
```

## API端点

### 1. 系统相关

#### 1.1 根路径
- **URL**: `/`
- **方法**: GET
- **描述**: 获取API基本信息
- **响应示例**:
```json
{
  "name": "股票分析系统API",
  "version": "1.0.0",
  "status": "running",
  "timestamp": "2025-12-25 20:00:00",
  "endpoints": {
    "strategies": "/api/strategies",
    "stocks": "/api/stocks",
    "system": "/api/system",
    "data": "/api/data"
  }
}
```

#### 1.2 健康检查
- **URL**: `/health`
- **方法**: GET
- **描述**: 检查系统健康状态
- **响应示例**:
```json
{
  "status": "healthy",
  "timestamp": "2025-12-25 20:00:00",
  "database": {
    "sqlite": "ok",
    "duckdb": "ok"
  }
}
```

#### 1.3 系统信息
- **URL**: `/api/system/info`
- **方法**: GET
- **描述**: 获取系统配置信息
- **响应示例**:
```json
{
  "success": true,
  "data": {
    "name": "股票分析系统",
    "version": "1.0.0",
    "datasource": "akshare",
    "database": {
      "sqlite": "./data/stock_analysis.db",
      "duckdb": "./data/market_data.duckdb"
    }
  }
}
```

#### 1.4 系统统计
- **URL**: `/api/system/stats`
- **方法**: GET
- **描述**: 获取系统统计信息
- **响应示例**:
```json
{
  "success": true,
  "data": {
    "stocks": {
      "total": 564
    },
    "strategies": {
      "total": 5,
      "enabled": 3
    },
    "market_data": {
      "stock_count": 564,
      "record_count": 4171,
      "earliest_date": "2025-12-18",
      "latest_date": "2025-12-24"
    },
    "job_logs": {
      "total": 10
    }
  }
}
```

### 2. 股票相关

#### 2.1 获取股票列表
- **URL**: `/api/stocks`
- **方法**: GET
- **描述**: 获取股票列表
- **查询参数**:
  - `market`: 市场类型（SH/SZ/BJ）
  - `keyword`: 搜索关键词
  - `limit`: 返回记录数（默认100）
  - `offset`: 偏移量（默认0）
- **响应示例**:
```json
{
  "success": true,
  "data": [
    {
      "code": "000001",
      "name": "平安银行",
      "market_type": "SZ",
      "industry": "银行",
      "list_date": "1991-04-03",
      "status": "normal"
    }
  ],
  "pagination": {
    "total": 564,
    "limit": 100,
    "offset": 0,
    "has_more": true
  }
}
```

#### 2.2 获取股票详情
- **URL**: `/api/stocks/{stock_code}`
- **方法**: GET
- **描述**: 获取指定股票的详细信息
- **路径参数**:
  - `stock_code`: 股票代码
- **响应示例**:
```json
{
  "success": true,
  "data": {
    "code": "000001",
    "name": "平安银行",
    "market_type": "SZ",
    "industry": "银行",
    "list_date": "1991-04-03",
    "status": "normal",
    "updated_at": "2025-12-25 18:00:00"
  }
}
```

#### 2.3 获取股票日线数据
- **URL**: `/api/stocks/{stock_code}/daily`
- **方法**: GET
- **描述**: 获取股票的日线行情数据
- **路径参数**:
  - `stock_code`: 股票代码
- **查询参数**:
  - `start_date`: 开始日期（YYYY-MM-DD）
  - `end_date`: 结束日期（YYYY-MM-DD）
  - `limit`: 返回记录数（默认100）
- **响应示例**:
```json
{
  "success": true,
  "data": [
    {
      "code": "000001",
      "trade_date": "2025-12-24",
      "open": 10.50,
      "high": 10.80,
      "low": 10.40,
      "close": 10.75,
      "volume": 1000000,
      "amount": 10750000,
      "pct_change": 2.38
    }
  ],
  "count": 1
}
```

#### 2.4 获取股票最新数据
- **URL**: `/api/stocks/{stock_code}/latest`
- **方法**: GET
- **描述**: 获取股票的最新行情数据
- **路径参数**:
  - `stock_code`: 股票代码
- **响应示例**:
```json
{
  "success": true,
  "data": {
    "code": "000001",
    "trade_date": "2025-12-24",
    "close": 10.75,
    "pct_change": 2.38
  }
}
```

#### 2.5 搜索股票
- **URL**: `/api/stocks/search`
- **方法**: GET
- **描述**: 按代码或名称搜索股票
- **查询参数**:
  - `q`: 搜索关键词（必填）
  - `limit`: 返回记录数（默认20）
- **响应示例**:
```json
{
  "success": true,
  "data": [
    {
      "code": "000001",
      "name": "平安银行"
    }
  ],
  "count": 1
}
```

#### 2.6 更新股票列表
- **URL**: `/api/stocks/update`
- **方法**: POST
- **描述**: 手动触发股票列表更新
- **响应示例**:
```json
{
  "success": true,
  "data": {
    "added": 5,
    "updated": 559
  },
  "message": "股票列表更新成功"
}
```

#### 2.7 更新行情数据
- **URL**: `/api/stocks/market-data/update`
- **方法**: POST
- **描述**: 手动触发行情数据更新
- **请求体**:
```json
{
  "days": 5
}
```
- **响应示例**:
```json
{
  "success": true,
  "data": {
    "updated_count": 2820
  },
  "message": "行情数据更新成功"
}
```

#### 2.8 获取股票统计
- **URL**: `/api/stocks/stats`
- **方法**: GET
- **描述**: 获取股票统计信息
- **响应示例**:
```json
{
  "success": true,
  "data": {
    "stocks": {
      "total": 564,
      "sh": 200,
      "sz": 300,
      "bj": 64
    },
    "market_data": {
      "stock_count": 564,
      "record_count": 4171
    }
  }
}
```

### 3. 策略相关

#### 3.1 获取策略列表
- **URL**: `/api/strategies`
- **方法**: GET
- **描述**: 获取策略列表
- **查询参数**:
  - `enabled_only`: 是否只返回启用的策略（true/false）
- **响应示例**:
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "大涨后站稳5日线",
      "description": "单日涨幅超过8%，随后3天收盘价均高于5日均线",
      "rise_threshold": 8.0,
      "observation_days": 3,
      "ma_period": 5,
      "enabled": true,
      "created_at": "2025-12-25 10:00:00",
      "updated_at": "2025-12-25 10:00:00"
    }
  ],
  "count": 1
}
```

#### 3.2 获取策略详情
- **URL**: `/api/strategies/{strategy_id}`
- **方法**: GET
- **描述**: 获取指定策略的详细信息
- **路径参数**:
  - `strategy_id`: 策略ID
- **响应示例**:
```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "大涨后站稳5日线",
    "description": "单日涨幅超过8%，随后3天收盘价均高于5日均线",
    "rise_threshold": 8.0,
    "observation_days": 3,
    "ma_period": 5,
    "enabled": true,
    "created_at": "2025-12-25 10:00:00",
    "updated_at": "2025-12-25 10:00:00"
  }
}
```

#### 3.3 创建策略
- **URL**: `/api/strategies`
- **方法**: POST
- **描述**: 创建新策略
- **请求体**:
```json
{
  "name": "策略名称",
  "description": "策略描述",
  "rise_threshold": 8.0,
  "observation_days": 3,
  "ma_period": 5,
  "enabled": true
}
```
- **响应示例**:
```json
{
  "success": true,
  "data": {
    "id": 2
  },
  "message": "策略创建成功"
}
```

#### 3.4 更新策略
- **URL**: `/api/strategies/{strategy_id}`
- **方法**: PUT
- **描述**: 更新策略信息
- **路径参数**:
  - `strategy_id`: 策略ID
- **请求体**:
```json
{
  "name": "新策略名称",
  "description": "新描述",
  "enabled": false
}
```
- **响应示例**:
```json
{
  "success": true,
  "message": "策略更新成功"
}
```

#### 3.5 删除策略
- **URL**: `/api/strategies/{strategy_id}`
- **方法**: DELETE
- **描述**: 删除策略
- **路径参数**:
  - `strategy_id`: 策略ID
- **响应示例**:
```json
{
  "success": true,
  "message": "策略删除成功"
}
```

#### 3.6 执行策略
- **URL**: `/api/strategies/{strategy_id}/execute`
- **方法**: POST
- **描述**: 手动执行策略
- **路径参数**:
  - `strategy_id`: 策略ID
- **请求体**:
```json
{
  "start_date": "2025-12-01",
  "end_date": "2025-12-25"
}
```
- **响应示例**:
```json
{
  "success": true,
  "data": {
    "scanned_stocks": 564,
    "matched_count": 15,
    "execution_time": 4.36
  },
  "message": "策略执行成功"
}
```

#### 3.7 获取策略执行结果
- **URL**: `/api/strategies/{strategy_id}/results`
- **方法**: GET
- **描述**: 获取策略的执行结果
- **路径参数**:
  - `strategy_id`: 策略ID
- **查询参数**:
  - `limit`: 返回记录数（默认100）
  - `offset`: 偏移量（默认0）
- **响应示例**:
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "strategy_id": 1,
      "stock_code": "000001",
      "stock_name": "平安银行",
      "trigger_date": "2025-12-20",
      "trigger_price": 10.50,
      "rise_pct": 8.5,
      "observation_result": "满足条件",
      "created_at": "2025-12-25 19:00:00"
    }
  ],
  "pagination": {
    "total": 15,
    "limit": 100,
    "offset": 0,
    "has_more": false
  }
}
```

#### 3.8 启用策略
- **URL**: `/api/strategies/{strategy_id}/enable`
- **方法**: POST
- **描述**: 启用策略
- **路径参数**:
  - `strategy_id`: 策略ID
- **响应示例**:
```json
{
  "success": true,
  "message": "策略已启用"
}
```

#### 3.9 禁用策略
- **URL**: `/api/strategies/{strategy_id}/disable`
- **方法**: POST
- **描述**: 禁用策略
- **路径参数**:
  - `strategy_id`: 策略ID
- **响应示例**:
```json
{
  "success": true,
  "message": "策略已禁用"
}
```

### 4. 调度器相关

#### 4.1 获取调度任务列表
- **URL**: `/api/system/scheduler/jobs`
- **方法**: GET
- **描述**: 获取所有调度任务
- **响应示例**:
```json
{
  "success": true,
  "data": [
    {
      "id": "daily_stock_update",
      "name": "每日更新股票列表",
      "next_run_time": "2025-12-25 18:00:00",
      "trigger": "cron[hour='18', minute='0']"
    }
  ],
  "count": 4
}
```

#### 4.2 立即执行任务
- **URL**: `/api/system/scheduler/jobs/{job_id}/run`
- **方法**: POST
- **描述**: 立即执行指定的调度任务
- **路径参数**:
  - `job_id`: 任务ID
- **响应示例**:
```json
{
  "success": true,
  "message": "任务已触发执行"
}
```

#### 4.3 获取任务日志
- **URL**: `/api/system/scheduler/logs`
- **方法**: GET
- **描述**: 获取调度任务执行日志
- **查询参数**:
  - `limit`: 返回记录数（默认100）
  - `offset`: 偏移量（默认0）
- **响应示例**:
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "job_type": "execute_strategies",
      "job_name": "执行策略",
      "status": "success",
      "started_at": "2025-12-25 19:00:00",
      "completed_at": "2025-12-25 19:00:15",
      "duration": 15.2,
      "message": "成功: 3, 失败: 0, 总匹配: 15"
    }
  ],
  "pagination": {
    "total": 10,
    "limit": 100,
    "offset": 0,
    "has_more": false
  }
}
```

#### 4.4 启动调度器
- **URL**: `/api/system/scheduler/start`
- **方法**: POST
- **描述**: 启动调度器
- **响应示例**:
```json
{
  "success": true,
  "message": "调度器已启动"
}
```

#### 4.5 停止调度器
- **URL**: `/api/system/scheduler/stop`
- **方法**: POST
- **描述**: 停止调度器
- **响应示例**:
```json
{
  "success": true,
  "message": "调度器已停止"
}
```

### 5. 数据管理相关

#### 5.1 启动全量导入
- **URL**: `/api/data/import`
- **方法**: POST
- **描述**: 启动全量数据导入任务（后台执行）
- **请求体**（可选）:
```json
{
  "start_date": "2021-01-01",
  "end_date": "2024-12-25",
  "limit": 10,
  "skip": 0
}
```
- **响应示例**:
```json
{
  "success": true,
  "task_id": "uuid-string",
  "message": "全量导入任务已启动，请在后台执行"
}
```

#### 5.2 启动增量更新
- **URL**: `/api/data/update`
- **方法**: POST
- **描述**: 启动增量数据更新任务（后台执行）
- **请求体**（可选）:
```json
{
  "days": 5,
  "only_existing": true
}
```
- **响应示例**:
```json
{
  "success": true,
  "task_id": "uuid-string",
  "message": "增量更新任务已启动，请在后台执行"
}
```

#### 5.3 获取任务状态
- **URL**: `/api/data/tasks/{task_id}`
- **方法**: GET
- **描述**: 获取任务状态和进度
- **路径参数**:
  - `task_id`: 任务ID
- **响应示例**:
```json
{
  "success": true,
  "data": {
    "task_id": "uuid-string",
    "task_name": "全量数据导入",
    "status": "running",
    "progress": 45.5,
    "message": "正在导入... 1000/5000 (20.0%), 预计剩余 120.0 分钟",
    "created_at": "2024-12-25 10:00:00",
    "started_at": "2024-12-25 10:00:01",
    "completed_at": null,
    "error": null,
    "is_running": true
  }
}
```

#### 5.4 获取任务列表
- **URL**: `/api/data/tasks`
- **方法**: GET
- **描述**: 获取任务列表
- **查询参数**:
  - `status`: 状态过滤（可选：pending|running|completed|failed）
  - `limit`: 返回记录数（默认10）
- **响应示例**:
```json
{
  "success": true,
  "data": [
    {
      "task_id": "uuid-string",
      "task_name": "全量数据导入",
      "status": "running",
      "progress": 45.5
    }
  ],
  "count": 1
}
```

#### 5.5 取消任务
- **URL**: `/api/data/tasks/{task_id}/cancel`
- **方法**: POST
- **描述**: 取消正在运行的任务
- **路径参数**:
  - `task_id`: 任务ID
- **响应示例**:
```json
{
  "success": true,
  "message": "任务已请求取消"
}
```

#### 5.6 获取数据状态
- **URL**: `/api/data/status`
- **方法**: GET
- **描述**: 获取数据统计状态
- **响应示例**:
```json
{
  "success": true,
  "data": {
    "total_stocks": 5000,
    "total_records": 1250000,
    "earliest_date": "2021-01-01",
    "latest_date": "2024-12-25",
    "record_count_millions": 125.0
  }
}
```

## 错误码

| 状态码 | 说明 |
|--------|------|
| 200 | 请求成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |
| 503 | 服务不可用 |

## 使用示例

### Python示例
```python
import requests

# 获取股票列表
response = requests.get('http://localhost:5000/api/stocks?limit=10')
data = response.json()
print(data)

# 创建策略
payload = {
    'name': '测试策略',
    'rise_threshold': 8.0,
    'observation_days': 3,
    'ma_period': 5,
    'enabled': True
}
response = requests.post('http://localhost:5000/api/strategies', json=payload)
print(response.json())

# 执行策略
strategy_id = 1
response = requests.post(f'http://localhost:5000/api/strategies/{strategy_id}/execute')
print(response.json())
```

### cURL示例
```bash
# 获取系统信息
curl http://localhost:5000/api/system/info

# 创建策略
curl -X POST http://localhost:5000/api/strategies \
  -H "Content-Type: application/json" \
  -d '{
    "name": "测试策略",
    "rise_threshold": 8.0,
    "observation_days": 3,
    "ma_period": 5,
    "enabled": true
  }'

# 执行策略
curl -X POST http://localhost:5000/api/strategies/1/execute
```

## 注意事项

1. 所有日期格式使用 `YYYY-MM-DD`
2. 所有时间格式使用 `YYYY-MM-DD HH:MM:SS`
3. 分页查询默认limit为100，最大不超过1000
4. API支持CORS，可以从任何域名访问
5. 建议在生产环境中添加认证和授权机制
