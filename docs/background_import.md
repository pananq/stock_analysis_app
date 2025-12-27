# 后台数据导入功能使用说明

## 功能概述

数据导入功能已优化为后台任务模式，支持长时间运行的数据导入和更新操作。用户发起导入请求后，任务在后台自动执行，无需一直等待页面响应。

## 主要特性

### 1. 后台任务执行
- 导入任务立即返回任务ID
- 任务在后台线程中运行
- 用户可以关闭页面，任务继续执行

### 2. 实时进度查询
- 每3秒自动查询任务进度
- 显示任务百分比和详细消息
- 支持任务状态：等待中、运行中、已完成、失败

### 3. 自动恢复
- 页面刷新后自动检测正在运行的任务
- 自动恢复进度显示
- 任务完成后自动更新数据统计

## API接口

### 1. 启动全量导入
```http
POST /api/data/import
Content-Type: application/json

{
  "start_date": "2021-01-01",  // 可选，默认3年前
  "end_date": "2024-12-25",    // 可选，默认今天
  "limit": 10,                 // 可选，用于测试
  "skip": 0                    // 可选，跳过前N只股票
}

Response:
{
  "success": true,
  "task_id": "uuid-string",
  "message": "全量导入任务已启动，请在后台执行"
}
```

### 2. 启动增量更新
```http
POST /api/data/update
Content-Type: application/json

{
  "days": 5,                   // 可选，更新最近N天，默认5
  "only_existing": true        // 可选，只更新已有数据，默认true
}

Response:
{
  "success": true,
  "task_id": "uuid-string",
  "message": "增量更新任务已启动，请在后台执行"
}
```

### 3. 查询任务状态
```http
GET /api/data/tasks/{task_id}

Response:
{
  "success": true,
  "data": {
    "task_id": "uuid-string",
    "task_name": "任务名称",
    "status": "running",  // pending|running|completed|failed
    "progress": 45.5,     // 0-100
    "message": "正在导入...",
    "created_at": "2024-12-25 10:00:00",
    "started_at": "2024-12-25 10:00:01",
    "completed_at": null,
    "error": null,
    "is_running": true
  }
}
```

### 4. 获取任务列表
```http
GET /api/data/tasks?status=running&limit=10

Response:
{
  "success": true,
  "data": [...],
  "count": 5
}
```

### 5. 取消任务
```http
POST /api/data/tasks/{task_id}/cancel

Response:
{
  "success": true,
  "message": "任务已请求取消"
}
```

### 6. 获取数据状态
```http
GET /api/data/status

Response:
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

## 使用方法

### 通过Web界面

1. 访问数据管理页面
2. 点击"开始全量导入"或"开始增量更新"
3. 查看页面上的进度条和状态
4. 可关闭页面，任务继续执行
5. 重新访问页面，自动恢复进度显示

### 通过API调用

```python
import requests

# 1. 启动全量导入
response = requests.post('http://localhost:5000/api/data/import', json={
    'start_date': '2021-01-01',
    'end_date': '2024-12-25'
})
task_id = response.json()['task_id']

# 2. 查询进度
response = requests.get(f'http://localhost:5000/api/data/tasks/{task_id}')
task_data = response.json()['data']
print(f"进度: {task_data['progress']}% - {task_data['message']}")
```

## 任务进度说明

- **0%**: 准备阶段，获取股票列表
- **1%**: 开始导入，显示待导入数量
- **1-99%**: 正在逐个导入股票，每10只更新一次进度
- **100%**: 导入完成，显示统计信息

## 注意事项

1. **网络稳定性**: 导入过程中需要稳定的网络连接
2. **API频率限制**: 系统已自动控制请求频率（0.1-0.3秒）
3. **磁盘空间**: 确保有足够的磁盘空间存储历史数据
4. **并发限制**: 同时只运行一个导入任务

## 故障排查

### 任务卡住不动
1. 检查网络连接
2. 查看服务器日志
3. 尝试取消任务重新开始

### 进度不更新
1. 刷新页面，系统会自动检测运行中的任务
2. 检查API服务是否正常运行
3. 查看浏览器控制台错误

### 导入失败
1. 查看任务错误信息
2. 检查数据源API是否可用
3. 查看服务器日志获取详细错误

## 性能参考

- **全量导入**: 5000只股票约需3-5小时
- **增量更新**: 5000只股票约需30-60分钟
- **单股票**: 平均0.2秒/只

## 后续优化方向

1. 支持断点续传
2. 支持多线程并行导入
3. 添加邮件通知完成状态
4. 支持定时任务自动导入
5. 添加导入历史记录查询
