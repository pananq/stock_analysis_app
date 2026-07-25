# 股海罗盘

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
- **跨市场日线**: 关注列表支持 A 股、港股和美股日线曲线及数据源自动回退
- **智能分析日报**: 支持基础技术分析、可配置 AI 综合解读与 SMTP 邮件日报
- **API频率控制**: 智能的请求延迟和重试机制，避免被数据源封禁
- **高性能存储**: MySQL存储所有数据，使用SQLAlchemy ORM访问，支持复杂查询和事务
- **响应式设计**: Web界面支持桌面和移动设备访问

## 🚀 快速开始

### 安装和部署

详细的安装和部署说明请参考 **[安装部署指南 (INSTALL.md)](INSTALL.md)**，包括：

- 📦 **快速安装**: 开发环境快速搭建
- 🏭 **生产部署**: 完整的生产环境部署步骤
- ⚙️ **配置说明**: 详细的配置项说明
- 🔧 **故障排查**: 常见问题解决方案
- 🐳 **Docker部署**: 容器化部署方案

### 快速启动

```bash
# 1. 克隆项目
git clone https://github.com/pananq/stock_analysis_app.git
cd stock_analysis_app

# 2. 安装依赖
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. 配置和初始化
cp config.example.yaml config.yaml
cp .env.example .env
# 必须在 .env 中设置随机 AUTH_SECRET_KEY；首次初始化还需设置
# ADMIN_INITIAL_PASSWORD。AI、SMTP 和 Tushare 密钥也建议放在此文件。
python main.py doctor
python main.py --init-db

# 4. 启动服务
python main.py start

# 5. 访问系统
# Web界面: http://localhost:8000
# 智能日报: http://localhost:8000/reports
```

更多详细说明请查看 [INSTALL.md](INSTALL.md)

##  项目结构

```
stock_analysis_app/
├── app/                          # 应用程序代码
│   ├── api/                      # REST API接口
│   │   ├── routes/               # API路由
│   │   └── app.py                # API应用
│   ├── web/                      # Web界面
│   │   ├── routes/               # Web路由
│   │   └── app.py                # Web应用
│   ├── models/                   # MySQL / SQLAlchemy 数据模型
│   ├── services/                 # 业务服务
│   │   ├── datasource.py         # 数据源抽象接口
│   │   ├── akshare_datasource.py # Akshare数据源
│   │   ├── tushare_datasource.py # Tushare数据源
│   │   ├── stock_service.py      # 股票服务
│   │   ├── market_data_service.py# A 股行情服务
│   │   ├── global_market_data_service.py # 港美股行情适配
│   │   ├── daily_report_service.py # 关注列表日报
│   │   ├── ai_analysis_service.py # AI 综合分析
│   │   ├── email_service.py      # SMTP 邮件发送
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
│   ├── test_new_features.py      # 当前维护的隔离与 API 集成测试
│   └── run_tests.py              # 测试运行脚本
├── docs/                         # 文档目录
│   ├── background_import.md      # 后台导入说明
│   └── daemon_mode_usage.md      # 后台运行使用指南
├── data/                         # 本地导出及备份目录
├── logs/                         # 日志文件
│   └── app.log                   # 应用日志
├── config.example.yaml           # 可提交的配置模板
├── .env.example                  # 敏感环境变量模板
├── requirements.txt              # Python依赖
├── main.py                       # 主入口（支持后台运行）
├── run_api.py                    # API启动脚本
└── run_web.py                    # Web启动脚本
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
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2021-01-01",
    "end_date": "2024-12-25"
  }'

# 返回任务ID，后续可查询进度
# {"success": true, "task_id": "uuid-string"}

# 查询任务进度
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:5000/api/data/tasks/{task_id}
```

#### 2. 增量更新（后台任务）
每日收盘后更新最新数据：

```bash
# 通过Web界面
# 访问 http://localhost:8000/data
# 点击"开始增量更新"

# 通过API
curl -X POST -H "Authorization: Bearer $TOKEN" \
  http://localhost:5000/api/data/update
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
  -H "Authorization: Bearer $TOKEN" \
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
curl -X POST -H "Authorization: Bearer $TOKEN" \
  http://localhost:5000/api/strategies/{id}/execute

# 或通过Web界面
# 访问 http://localhost:8000/strategies
# 点击策略列表中的"执行"按钮
```

### 股票查询

#### 1. 查询股票列表
```bash
# 查询所有股票
curl -H "Authorization: Bearer $TOKEN" http://localhost:5000/api/stocks

# 按条件查询
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:5000/api/stocks?market=沪市&industry=银行"
```

#### 2. 查询历史行情
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:5000/api/stocks/600000/history?limit=30"
```

## 🧪 测试

### 运行当前快速回归测试
```bash
cd stock_analysis_app
.venv/bin/python -m tests.run_tests --quick
.venv/bin/python -m unittest discover -s tests -p "test*.py"
```

该测试集不访问外部网络或生产数据库，使用内存数据库验证认证、跨市场关注列表、日线指标、
AI 故障降级、日报、邮件编排和 API Token 生命周期。旧版 SQLite/DuckDB 测试保留在
`tests/legacy/`，默认测试发现不会执行这些可能访问外部服务的历史脚本。

配置 AI 后，可显式运行真实港美股行情与 AI 日报验证；脚本会创建并清理临时 MySQL 记录：

```bash
.venv/bin/python tools/verify_live_ai_report.py --confirm-live
```

配置 SMTP 和日报收件人后，可显式发送一封真实验证邮件；脚本只输出收件人数，不显示地址：

```bash
.venv/bin/python tools/verify_live_email.py --confirm-send
```

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

更多问题请参考 [安装部署指南 (INSTALL.md)](INSTALL.md) 中的故障排查部分。

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
