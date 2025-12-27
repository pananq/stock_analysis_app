# 股票分析系统

一个基于Python的A股股票数据分析和策略执行系统，支持历史行情获取、技术指标计算、策略配置和自动化执行。

## 📋 功能特性

### 核心功能
- **股票数据管理**: 自动获取和更新A股股票列表和历史行情数据
- **技术指标计算**: 支持移动平均线(MA)、涨跌幅等常用技术指标
- **策略管理**: 支持创建、编辑、删除和执行自定义策略
- **自动化调度**: 定时任务自动更新数据和执行策略
- **Web界面**: 友好的Web管理界面，支持数据可视化
- **任务执行详情**: 详细记录每次任务执行结果，包括每只股票的导入/匹配情况

### 技术特点
- **多数据源支持**: 支持Akshare和Tushare数据源，可灵活切换
- **API频率控制**: 智能的请求延迟和重试机制，避免被数据源封禁
- **高性能存储**: MySQL存储所有数据，使用SQLAlchemy ORM访问，支持复杂查询和事务
- **响应式设计**: Web界面支持桌面和移动设备访问

## 🚀 快速开始

### 环境要求
- Python 3.8+
- pip 包管理器

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd stock-analysis-app
```

2. **创建虚拟环境（推荐）**
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **初始化配置**
```bash
cp config.yaml.example config.yaml
# 编辑 config.yaml 配置数据源和其他选项
```

5. **初始化数据库**
```bash
python main.py --init-db
```

### 启动服务

#### 方式一：使用主程序启动（推荐）

**后台运行（默认）** - 适合生产环境

```bash
# 启动所有服务（API + Web + 调度器）- 后台运行
python main.py

# 或使用显式命令
python main.py start

# 只启动API服务（含调度器）
python main.py start --api-only

# 只启动Web服务
python main.py start --web-only
```

**前台运行** - 适合开发环境，可查看实时日志

```bash
# 启动所有服务（前台运行）
python main.py start --foreground
python main.py start -f
```

**服务管理命令**

```bash
# 停止服务
python main.py stop

# 查看服务状态
python main.py status

# 重启服务
python main.py restart
```

**使用说明**：
- 默认启动方式为后台运行，服务会在后台持续运行
- 使用 `stop` 命令可以优雅地停止所有服务
- 使用 `status` 命令可以查看服务运行状态和最近日志
- 日志文件位置：`logs/app.log`
- PID文件位置：`.stock_app.pid`

详细使用说明请参考 [docs/daemon_mode_usage.md](docs/daemon_mode_usage.md)

#### 方式二：分别启动服务

```bash
# 启动API服务器（端口5000）
python run_api.py

# 启动Web服务器（端口8000）
python run_web.py
```

### 访问系统
- **Web界面**: http://localhost:8000
- **API文档**: http://localhost:5000/api/docs

## 📁 项目结构

```
stock-analysis-app/
├── app/                          # 应用程序代码
│   ├── api/                      # REST API接口
│   │   ├── routes/               # API路由
│   │   └── app.py                # API应用
│   ├── web/                      # Web界面
│   │   ├── routes/               # Web路由
│   │   └── app.py                # Web应用
│   ├── models/                   # 数据模型
│   │   ├── sqlite_db.py          # SQLite数据库管理
│   │   └── duckdb_manager.py     # DuckDB数据库管理
│   ├── services/                 # 业务服务
│   │   ├── datasource.py         # 数据源抽象接口
│   │   ├── akshare_datasource.py # Akshare数据源
│   │   ├── tushare_datasource.py # Tushare数据源
│   │   ├── stock_service.py      # 股票服务
│   │   ├── market_data_service.py# 行情数据服务
│   │   ├── strategy_service.py   # 策略服务
│   │   └── strategy_executor.py  # 策略执行器
│   ├── scheduler/                # 任务调度
│   │   └── task_scheduler.py     # 调度器
│   ├── task_manager.py           # 后台任务管理
│   ├── indicators/               # 技术指标
│   │   └── technical_indicators.py
│   ├── utils/                    # 工具模块
│   │   ├── config.py             # 配置管理
│   │   ├── logger.py             # 日志管理
│   │   └── rate_limiter.py       # 频率控制
│   ├── templates/                # HTML模板
│   └── static/                   # 静态资源
├── tests/                        # 测试代码
│   ├── test_integration.py       # 集成测试
│   ├── test_rate_limiter.py      # 频率控制测试
│   ├── test_datasource.py        # 数据源测试
│   ├── test_performance.py       # 性能测试
│   └── run_tests.py              # 测试运行脚本
├── docs/                         # 文档目录
│   ├── background_import.md      # 后台导入说明
│   └── daemon_mode_usage.md      # 后台运行使用指南
├── data/                         # 数据文件
│   ├── stocks.db                 # SQLite数据库
│   └── market_data.duckdb        # DuckDB数据库
├── logs/                         # 日志文件
│   └── app.log                   # 应用日志
├── config.yaml                   # 配置文件
├── requirements.txt              # Python依赖
├── main.py                       # 主入口（支持后台运行）
├── run_api.py                    # API启动脚本
└── run_web.py                    # Web启动脚本
```

## ⚙️ 配置说明

### 配置文件 (config.yaml)

```yaml
# 数据源配置
datasource:
  default: akshare          # 默认数据源
  akshare:
    enabled: true
  tushare:
    enabled: false
    token: your_tushare_token  # Tushare Token

# API频率控制
api_rate_limit:
  min_delay: 0.1            # 最小延迟（秒）
  max_delay: 0.3            # 最大延迟（秒）
  max_retries: 3            # 最大重试次数

# 数据库配置
database:
  type: mysql
  mysql:
    host: localhost
    port: 3306
    username: your_username
    password: your_password
    database: stock_analysis

# API服务器配置
api:
  host: 0.0.0.0
  port: 5000
  debug: false

# Web服务器配置
web:
  host: 0.0.0.0
  port: 8000
  debug: false

# 调度任务配置
scheduler:
  enabled: true
  update_stock_list:
    hour: 18
    minute: 0
  update_market_data:
    hour: 19
    minute: 0

# 日志配置
logging:
  level: INFO
  file: logs/app.log
  max_size: 10485760        # 10MB
  backup_count: 5
```

## 📊 使用指南

### 数据导入

#### 1. 全量导入（后台任务）
首次使用时，需要导入全量数据。导入任务在后台执行，无需等待：

```bash
# 通过Web界面（推荐）
# 访问 http://localhost:8000/data
# 点击"开始全量导入"
# 任务会在后台运行，显示实时进度

# 通过API
curl -X POST http://localhost:5000/api/data/import \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2021-01-01",
    "end_date": "2024-12-25"
  }'

# 返回任务ID，后续可查询进度
# {"success": true, "task_id": "uuid-string"}

# 查询任务进度
curl http://localhost:5000/api/data/tasks/{task_id}
```

#### 2. 增量更新（后台任务）
每日收盘后更新最新数据：

```bash
# 通过Web界面
# 访问 http://localhost:8000/data
# 点击"开始增量更新"

# 通过API
curl -X POST http://localhost:5000/api/data/update
```

**注意**：
- 导入任务在后台运行，可以关闭页面
- 重新访问页面会自动恢复进度显示
- 5000只股票全量导入约需3-5小时
- 详细使用说明请参考 [docs/background_import.md](docs/background_import.md)
- 如果服务在后台运行，可以通过 `python main.py status` 查看日志

### 策略管理

#### 1. 创建策略
```bash
# 通过API
curl -X POST http://localhost:5000/api/strategies \
  -H "Content-Type: application/json" \
  -d '{
    "name": "均线突破策略",
    "description": "当股价突破20日均线时买入",
    "config": {
      "min_change": 0,
      "max_change": 5,
      "days": 20,
      "ma_period": 20
    },
    "enabled": true
  }'
```

#### 2. 执行策略
```bash
# 通过API
curl -X POST http://localhost:5000/api/strategies/{id}/execute

# 或通过Web界面
# 访问 http://localhost:8000/strategies
# 点击策略列表中的"执行"按钮
```

### 股票查询

#### 1. 查询股票列表
```bash
# 查询所有股票
curl http://localhost:5000/api/stocks

# 按条件查询
curl "http://localhost:5000/api/stocks?market=沪市&industry=银行"
```

#### 2. 查询历史行情
```bash
curl "http://localhost:5000/api/stocks/600000/history?limit=30"
```

## 🧪 测试

### 运行所有测试
```bash
cd stock-analysis-app
python -m tests.run_tests
```

### 运行快速测试（不含网络请求）
```bash
python -m tests.run_tests --quick
```

### 运行指定模块测试
```bash
# 集成测试
python -m tests.run_tests --module integration

# 频率控制测试
python -m tests.run_tests --module rate_limiter

# 数据源测试
python -m tests.run_tests --module datasource

# 性能测试
python -m tests.run_tests --module performance
```

## 📈 性能指标

- **策略执行**: 全市场扫描在5分钟内完成
- **数据查询**: 单股票历史行情查询 < 100ms
- **API响应**: 平均响应时间 < 200ms
- **并发支持**: 支持多用户同时访问

## 🔧 开发指南

### 添加新的数据源

1. 继承 `DataSource` 抽象类
2. 实现必要的方法：
   - `get_stock_list()`: 获取股票列表
   - `get_stock_history()`: 获取历史行情
   - `get_name()`: 返回数据源名称

```python
from app.services.datasource import DataSource

class MyDataSource(DataSource):
    def get_stock_list(self):
        # 实现获取股票列表
        pass
    
    def get_stock_history(self, stock_code, start_date, end_date):
        # 实现获取历史行情
        pass
    
    def get_name(self):
        return 'my_datasource'
```

3. 在 `DataSourceFactory` 中注册新数据源

### 添加新的技术指标

在 `app/indicators/technical_indicators.py` 中添加新方法：

```python
def calculate_rsi(self, prices: List[float], period: int = 14) -> List[float]:
    """计算RSI指标"""
    # 实现RSI计算逻辑
    pass
```

## ❓ 常见问题

### 服务管理

**Q: 如何启动和停止服务？**
```bash
# 后台启动所有服务
python main.py

# 停止服务
python main.py stop

# 查看服务状态
python main.py status

# 重启服务
python main.py restart
```

**Q: 服务启动后看不到日志输出？**
A: 默认启动方式为后台运行，日志会写入 `logs/app.log` 文件。你可以：
- 使用 `tail -f logs/app.log` 查看实时日志
- 使用 `python main.py status` 查看服务状态和最近的日志
- 使用 `python main.py start --foreground` 前台运行查看实时输出

**Q: 服务无法停止怎么办？**
A: 检查PID文件 `.stock_app.pid` 中的进程是否还存在，如果存在可以手动杀死：
```bash
# 查看PID
cat .stock_app.pid

# 手动停止进程
kill $(cat .stock_app.pid)

# 或强制停止
kill -9 $(cat .stock_app.pid)

# 清理PID文件
rm .stock_app.pid
```

**Q: 如何知道服务是否正在运行？**
```bash
python main.py status
```

### 数据导入

### 1. 数据导入失败
- 检查网络连接
- 检查数据源配置
- 查看日志文件 `logs/app.log`
- 确认服务已启动：`python main.py status`

### 2. API请求被限制
- 系统已内置频率控制机制
- 可调整 `config.yaml` 中的 `api_rate_limit` 配置

### 3. Web界面无法访问
- 确认API服务器已启动：`python main.py status`
- 检查端口是否被占用
- 确认防火墙设置

### 4. 策略执行缓慢
- 检查数据库索引是否创建
- 考虑增加系统内存
- 优化策略条件

**Q: 后台运行和前台运行有什么区别？**
A: 
- **后台运行**：服务在后台运行，不会占用终端窗口，适合生产环境
- **前台运行**：服务在终端窗口运行，可以实时查看日志，适合开发环境

## 📝 更新日志

### v1.1.0 (2025-12-26)
- 新增服务后台运行功能，支持守护进程模式
- 新增服务管理命令：start、stop、status、restart
- 支持前台运行模式，便于开发调试
- 优化日志管理，统一输出到日志文件
- 新增PID文件管理，防止重复启动
- 提供优雅停止机制，支持安全关闭

### v1.0.0 (2025-12-25)
- 初始版本发布
- 支持Akshare和Tushare数据源
- 实现股票数据管理、策略执行、Web界面
- 完成集成测试和性能优化

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📧 联系方式

如有问题，请提交Issue或联系开发者。
