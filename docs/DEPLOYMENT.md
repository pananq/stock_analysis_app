# 股海罗盘 部署指南

本文档涵盖从开发环境到生产环境的完整部署方案。

---

## 目录

1. [系统要求](#1-系统要求)
2. [快速启动（开发环境）](#2-快速启动开发环境)
3. [生产环境部署（systemd + Gunicorn）](#3-生产环境部署systemd--gunicorn)
4. [MCP 服务部署](#4-mcp-服务部署)
5. [Nginx 反向代理](#5-nginx-反向代理)
6. [SSL/TLS 配置](#6-ssltls-配置)
7. [数据库初始化](#7-数据库初始化)
8. [配置参考](#8-配置参考)
9. [运维操作](#9-运维操作)
10. [故障排查](#10-故障排查)

---

## 1. 系统要求

| 组件 | 最低版本 | 说明 |
|------|---------|------|
| Python | 3.10+ | 建议 3.11 |
| MySQL | 5.7+ / 8.0 | 主数据库 |
| 内存 | 2GB+ | 生产环境建议 4GB |
| 磁盘 | 10GB+ | 历史行情数据约 5GB |

---

## 2. 快速启动（开发环境）

```bash
# 1. 克隆项目
git clone <repo-url>
cd stock-analysis-app

# 2. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置
cp config.example.yaml config.yaml
# 编辑 config.yaml，填入 MySQL 连接信息和 Tushare/Akshare Token

# 5. 初始化数据库
python main.py --init-db

# 6. 启动（前台模式，便于调试）
python main.py start --foreground
```

**默认端口：**
- API 服务：`http://localhost:5000`
- Web 界面：`http://localhost:8000`
- MCP 服务：`http://localhost:5002`

---

## 3. 生产环境部署（systemd + Gunicorn）

### 3.1 API 服务（Gunicorn）

项目已包含 systemd 服务文件。

```bash
# 复制服务文件
sudo cp stock-api.service /etc/systemd/system/
sudo cp stock-web.service /etc/systemd/system/

# 根据实际路径修改服务文件中的 WorkingDirectory 和 User
sudo nano /etc/systemd/system/stock-api.service
sudo nano /etc/systemd/system/stock-web.service

# 启用并启动
sudo systemctl daemon-reload
sudo systemctl enable stock-api stock-web
sudo systemctl start stock-api stock-web

# 检查状态
sudo systemctl status stock-api stock-web
```

### 3.2 MCP 服务（systemd）

创建 MCP 服务文件：

```bash
sudo nano /etc/systemd/system/stock-mcp.service
```

```ini
[Unit]
Description=Stock Analysis MCP Server
After=network.target mysql.service stock-api.service

[Service]
Type=simple
User=aaronpan
Group=aaronpan
WorkingDirectory=/data/home/aaronpan/stock-analysis-app
Environment=PATH=/data/home/aaronpan/stock-analysis-app/venv/bin
ExecStart=/data/home/aaronpan/stock-analysis-app/venv/bin/python -c \
    "from app.mcp.server import run_mcp_server; run_mcp_server()"
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable stock-mcp
sudo systemctl start stock-mcp
sudo systemctl status stock-mcp
```

### 3.3 一键部署脚本

```bash
# 使用现有自动部署脚本（仅 API + Web）
sudo ./deploy_gunicorn.sh
```

---

## 4. MCP 服务部署

MCP（Model Context Protocol）服务允许 Claude Desktop 等 AI 工具直接查询关注列表和股票数据。

### 4.1 配置

`config.yaml` 中的 MCP 配置：

```yaml
mcp:
  host: 0.0.0.0   # 监听地址
  port: 5002       # 监听端口
  enabled: true    # 是否启用
```

### 4.2 生成 API Token

MCP 客户端使用长期 API Token 认证（不使用 JWT），在 Web 界面生成：

1. 访问 `http://localhost:8000/api-tokens`
2. 点击"生成新 Token"
3. 输入名称（如 "Claude Desktop"）
4. **立即复制明文 Token**（`sk-xxxx...`），关闭窗口后无法再查看

也可以通过 API 生成：

```bash
# 先登录获取 JWT
JWT=$(curl -s -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your-password"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

# 生成 API Token
curl -X POST http://localhost:5000/api/tokens \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"name":"Claude Desktop"}'
# 返回: {"success":true,"token":"sk-xxx...","prefix":"sk-ab12","id":1}
```

### 4.3 配置 Claude Desktop

编辑 Claude Desktop 配置文件（`~/Library/Application Support/Claude/claude_desktop_config.json`）：

```json
{
  "mcpServers": {
    "stock-analysis": {
      "url": "http://your-server:5002/sse",
      "headers": {
        "Authorization": "Bearer sk-your-token-here"
      }
    }
  }
}
```

### 4.4 可用 MCP 工具

| 工具 | 参数 | 说明 |
|------|------|------|
| `get_watchlist` | `group?`, `tag?` | 获取关注列表 |
| `add_to_watchlist` | `stock_code`, `market?`, `group?`, `tags?`, `notes?` | 添加关注 |
| `remove_from_watchlist` | `watchlist_id` | 移除关注 |
| `get_stock_data` | `stock_code`, `start_date?`, `end_date?`, `market?` | 查询 OHLCV 数据 |
| `get_stock_indicators` | `stock_code`, `start_date?`, `end_date?`, `ma_periods?` | 查询均线指标 |

---

## 5. Nginx 反向代理

推荐使用 Nginx 作为反向代理，统一对外端口并处理 SSL。

```nginx
# /etc/nginx/sites-available/stock-analysis
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate     /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # Web 界面
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # API 服务
    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # MCP SSE 服务（需要关闭缓冲，支持 Server-Sent Events）
    location /mcp/ {
        proxy_pass http://127.0.0.1:5002/;
        proxy_http_version 1.1;
        proxy_set_header Connection '';
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 86400;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/stock-analysis /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 6. SSL/TLS 配置

详细 SSL 配置参见 [SSL_README.md](SSL_README.md)。

**快速自签名证书（开发/测试）：**

```bash
mkdir -p ssl
openssl req -x509 -newkey rsa:4096 -keyout ssl/server.key \
    -out ssl/server.crt -days 365 -nodes \
    -subj "/CN=localhost"
```

在 `config.yaml` 中启用：

```yaml
api:
  ssl_enabled: true
  ssl_cert: ./ssl/server.crt
  ssl_key: ./ssl/server.key
```

---

## 7. 数据库初始化

### 7.1 创建 MySQL 数据库和用户

```sql
CREATE DATABASE stock_analysis CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'saapp'@'localhost' IDENTIFIED BY 'your-password';
GRANT ALL PRIVILEGES ON stock_analysis.* TO 'saapp'@'localhost';
FLUSH PRIVILEGES;
```

### 7.2 初始化表结构

```bash
source venv/bin/activate
python main.py --init-db
```

这会自动创建所有表，包括：
- `users` — 用户账号
- `stocks` — 股票元数据
- `daily_market` — 日线行情
- `strategies` / `strategy_results` — 策略管理
- `watchlists` — 用户关注列表（新增）
- `api_tokens` — 长期 API Token（新增）
- `job_logs` / `task_execution_details` — 任务日志

### 7.3 导入历史数据（可选）

```bash
# 通过 Web 界面：访问 /data → 全量导入历史数据
# 或通过 API：
curl -X POST http://localhost:5000/api/data/import \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"start_date":"2022-01-01"}'
```

---

## 8. 配置参考

`config.yaml` 关键配置项：

```yaml
# API 服务
api:
  host: 0.0.0.0
  port: 5000
  debug: false          # 生产环境必须 false
  cors_origins: "*"     # 生产环境限制为具体域名

# Web 服务
web:
  host: 0.0.0.0
  port: 8000
  secret_key: "换成随机字符串"   # 重要：生产环境必须修改

# 数据库
database:
  type: mysql
  mysql:
    host: localhost
    port: 3306
    database: stock_analysis
    username: saapp          # 注意：字段名是 username（不是 user）
    password: your-password

# 数据源（二选一）
datasource:
  type: tushare             # 或 akshare
  tushare:
    token: "your-tushare-token"

# MCP 服务
mcp:
  host: 0.0.0.0
  port: 5002
  enabled: true

# 认证
auth:
  secret_key: "换成随机字符串"   # 重要：生产环境必须修改
  token_expire_hours: 24
```

> ⚠️ **生产环境必改项：**
> - `web.secret_key`
> - `auth.secret_key`
> - `database.mysql.password`

---

## 9. 运维操作

### 服务管理

```bash
# 开发模式
python main.py start          # 后台启动
python main.py start -f       # 前台启动（调试）
python main.py stop           # 停止
python main.py status         # 查看状态
python main.py restart        # 重启

# 只启动 API（不启动 Web 和 MCP）
python main.py start --api-only

# 生产模式（systemd）
sudo systemctl start|stop|restart|status stock-api stock-web stock-mcp
```

### 查看日志

```bash
# 应用日志
tail -f logs/app.log

# systemd 日志
sudo journalctl -u stock-api -f
sudo journalctl -u stock-mcp -f
```

### 关注列表管理

```bash
# 添加股票到关注列表
curl -X POST http://localhost:5000/api/watchlist \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"stock_code":"600000","group_name":"持仓","tags":"银行"}'

# 查询关注列表
curl http://localhost:5000/api/watchlist \
  -H "Authorization: Bearer $JWT"

# 按分组筛选
curl -G http://localhost:5000/api/watchlist \
  --data-urlencode "group=持仓" \
  -H "Authorization: Bearer $JWT"

# 按标签筛选
curl -G http://localhost:5000/api/watchlist \
  --data-urlencode "tag=银行" \
  -H "Authorization: Bearer $JWT"

# 查询股票数据+均线指标
curl "http://localhost:5000/api/watchlist/600000/data?ma_periods=5,30,60" \
  -H "Authorization: Bearer $JWT"
```

### API Token 管理

```bash
# 列出所有 Token
curl http://localhost:5000/api/tokens \
  -H "Authorization: Bearer $JWT"

# 创建 Token
curl -X POST http://localhost:5000/api/tokens \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"name":"Claude Desktop"}'

# 撤销 Token
curl -X DELETE http://localhost:5000/api/tokens/1 \
  -H "Authorization: Bearer $JWT"
```

---

## 10. 故障排查

### 端口占用

```bash
# 查看端口占用
ss -tlnp | grep -E '5000|8000|5002'

# 停止占用进程
python main.py stop
# 或强制杀死
kill -9 $(lsof -ti:5000)
```

### 数据库连接失败

```bash
# 检查 MySQL 状态
sudo systemctl status mysql

# 测试连接
mysql -u saapp -p stock_analysis -e "SELECT 1"

# 检查 config.yaml 中的 username 字段（不是 user）
grep -A5 "mysql:" config.yaml
```

### MCP 服务无法连接

1. 确认 `config.yaml` 中 `mcp.enabled: true`
2. 检查端口是否监听：`ss -tlnp | grep 5002`
3. 检查日志：`grep -i mcp logs/app.log`
4. 确认 API Token 未撤销：访问 `/api-tokens` 页面

### 均线数据为空

股票历史数据可能未导入。通过 Web 界面的「数据管理」→「全量导入」导入历史行情，或使用 API 触发导入。

### 关注列表 CRUD 报错

确认 `watchlists` 和 `api_tokens` 表已创建：

```bash
python main.py --init-db
# 或直接检查
mysql -u saapp -p stock_analysis -e "SHOW TABLES LIKE 'watchlists';"
```
