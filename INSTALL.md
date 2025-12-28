# 安装部署指南

本文档提供股票分析系统的详细安装和部署说明。

## 📋 目录

- [快速开始](#快速开始)
- [生产环境部署](#生产环境部署)
- [配置说明](#配置说明)
- [服务管理](#服务管理)
- [备份策略](#备份策略)
- [监控和维护](#监控和维护)
- [故障排查](#故障排查)

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

## 🏭 生产环境部署

### 部署前准备

#### 1. 服务器要求
- **操作系统**: Linux (推荐 Ubuntu 20.04+ / CentOS 7+)
- **CPU**: 2核心以上
- **内存**: 4GB以上（推荐8GB）
- **磁盘**: 50GB以上可用空间
- **网络**: 稳定的互联网连接

#### 2. 软件依赖
- Python 3.8+
- MySQL 5.7+ 或 8.0+
- Git
- pip

### 部署步骤

#### 步骤1: 准备服务器环境

```bash
# 更新系统包
sudo apt update && sudo apt upgrade -y  # Ubuntu/Debian
# 或
sudo yum update -y  # CentOS/RHEL

# 安装Python 3.8+
sudo apt install python3 python3-pip python3-venv -y  # Ubuntu/Debian
# 或
sudo yum install python3 python3-pip -y  # CentOS/RHEL

# 安装Git
sudo apt install git -y  # Ubuntu/Debian
# 或
sudo yum install git -y  # CentOS/RHEL

# 验证安装
python3 --version
pip3 --version
git --version
```

#### 步骤2: 安装和配置MySQL

```bash
# 安装MySQL
sudo apt install mysql-server -y  # Ubuntu/Debian
# 或
sudo yum install mysql-server -y  # CentOS/RHEL

# 启动MySQL服务
sudo systemctl start mysql
sudo systemctl enable mysql

# 安全配置MySQL
sudo mysql_secure_installation

# 登录MySQL创建数据库和用户
sudo mysql -u root -p

# 在MySQL命令行中执行：
CREATE DATABASE stock_analysis CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'YOUR_DB_USERNAME'@'localhost' IDENTIFIED BY 'YOUR_SECURE_PASSWORD';
GRANT ALL PRIVILEGES ON stock_analysis.* TO 'YOUR_DB_USERNAME'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

#### 步骤3: 部署应用代码

```bash
# 创建应用目录
sudo mkdir -p /opt/stock-analysis
sudo chown $USER:$USER /opt/stock-analysis
cd /opt/stock-analysis

# 克隆代码（替换为你的仓库地址）
git clone <your-repository-url> .

# 或者使用scp/rsync从本地上传
# rsync -avz --exclude='venv' --exclude='*.pyc' --exclude='__pycache__' \
#   /path/to/local/stock-analysis-app/ user@server:/opt/stock-analysis/
```

#### 步骤4: 配置Python虚拟环境

```bash
# 创建虚拟环境
cd /opt/stock-analysis
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 升级pip
pip install --upgrade pip

# 安装依赖
pip install -r requirements.txt
```

#### 步骤5: 配置应用

```bash
# 复制配置文件模板
cp config.yaml.example config.yaml

# 编辑配置文件
vim config.yaml  # 或使用 nano config.yaml
```

**重要配置项**：

```yaml
# 应用模式（生产环境必须设置为production）
app_mode: production

# 数据源配置
datasource:
  default: tushare  # 或 akshare
  tushare:
    enabled: true
    token: YOUR_TUSHARE_TOKEN_HERE  # 替换为你的实际Token

# 数据库配置
database:
  type: mysql
  mysql:
    host: localhost
    port: 3306
    username: YOUR_DB_USERNAME
    password: YOUR_SECURE_PASSWORD  # 使用步骤2中设置的密码
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
  max_size: 10485760
  backup_count: 5
```

#### 步骤6: 初始化数据库

```bash
# 确保虚拟环境已激活
source venv/bin/activate

# 初始化数据库表结构
python main.py --init-db

# 验证数据库初始化
mysql -u YOUR_DB_USERNAME -p stock_analysis -e "SHOW TABLES;"
```

#### 步骤7: 配置系统服务（Systemd）

创建systemd服务文件，实现开机自启和服务管理：

```bash
# 创建服务文件
sudo vim /etc/systemd/system/stock-analysis.service
```

**服务文件内容**：

```ini
[Unit]
Description=Stock Analysis Application
After=network.target mysql.service
Wants=mysql.service

[Service]
Type=forking
User=YOUR_USERNAME
Group=YOUR_USERNAME
WorkingDirectory=/opt/stock-analysis
Environment="PATH=/opt/stock-analysis/venv/bin"
ExecStart=/opt/stock-analysis/venv/bin/python /opt/stock-analysis/main.py start
ExecStop=/opt/stock-analysis/venv/bin/python /opt/stock-analysis/main.py stop
ExecReload=/opt/stock-analysis/venv/bin/python /opt/stock-analysis/main.py restart
PIDFile=/opt/stock-analysis/.stock_app.pid
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
```

**注意**: 将 `YOUR_USERNAME` 替换为实际的Linux用户名。

```bash
# 重新加载systemd配置
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start stock-analysis

# 设置开机自启
sudo systemctl enable stock-analysis

# 查看服务状态
sudo systemctl status stock-analysis

# 查看日志
sudo journalctl -u stock-analysis -f
```

#### 步骤8: 配置防火墙

```bash
# Ubuntu/Debian (UFW)
sudo ufw allow 8000/tcp  # Web界面
sudo ufw allow 5000/tcp  # API接口（可选，如果需要外部访问）
sudo ufw enable

# CentOS/RHEL (firewalld)
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --permanent --add-port=5000/tcp
sudo firewall-cmd --reload
```

#### 步骤9: 配置Nginx反向代理（推荐）

使用Nginx作为反向代理可以提供更好的性能和安全性：

```bash
# 安装Nginx
sudo apt install nginx -y  # Ubuntu/Debian
# 或
sudo yum install nginx -y  # CentOS/RHEL

# 创建Nginx配置
sudo vim /etc/nginx/sites-available/stock-analysis
```

**Nginx配置内容**：

```nginx
server {
    listen 80;
    server_name YOUR_DOMAIN_OR_IP;  # 替换为你的域名或服务器IP

    # Web界面
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # API接口
    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 静态文件
    location /static/ {
        alias /opt/stock-analysis/app/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # 日志
    access_log /var/log/nginx/stock-analysis-access.log;
    error_log /var/log/nginx/stock-analysis-error.log;
}
```

```bash
# 启用配置
sudo ln -s /etc/nginx/sites-available/stock-analysis /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重启Nginx
sudo systemctl restart nginx
sudo systemctl enable nginx
```

#### 步骤10: 配置SSL证书（可选但推荐）

使用Let's Encrypt免费SSL证书：

```bash
# 安装Certbot
sudo apt install certbot python3-certbot-nginx -y  # Ubuntu/Debian
# 或
sudo yum install certbot python3-certbot-nginx -y  # CentOS/RHEL

# 获取SSL证书
sudo certbot --nginx -d YOUR_DOMAIN_OR_IP

# 自动续期
sudo certbot renew --dry-run
```

#### 步骤11: 初始化数据

```bash
# 登录Web界面
# 访问 http://YOUR_DOMAIN_OR_IP 或 http://YOUR_SERVER_IP

# 使用默认管理员账号登录
# 用户名: admin
# 密码: ******** (首次登录后请立即修改，默认密码请联系管理员获取)

# 进入数据管理页面，开始全量导入
# 导入任务会在后台运行，约需3-5小时
```

### 部署验证

```bash
# 1. 检查服务状态
sudo systemctl status stock-analysis

# 2. 检查进程
ps aux | grep python | grep main.py

# 3. 检查端口监听
sudo netstat -tlnp | grep -E '5000|8000'

# 4. 查看应用日志
tail -f /opt/stock-analysis/logs/app.log

# 5. 测试API接口
curl http://localhost:5000/health

# 6. 测试Web界面
curl http://localhost:8000/
```

### 服务管理命令

```bash
# 启动服务
sudo systemctl start stock-analysis

# 停止服务
sudo systemctl stop stock-analysis

# 重启服务
sudo systemctl restart stock-analysis

# 查看状态
sudo systemctl status stock-analysis

# 查看日志
sudo journalctl -u stock-analysis -f

# 或直接查看应用日志
tail -f /opt/stock-analysis/logs/app.log
```

### 更新部署

当需要更新应用时：

```bash
# 1. 进入应用目录
cd /opt/stock-analysis

# 2. 备份当前版本
sudo cp -r /opt/stock-analysis /opt/stock-analysis.backup.$(date +%Y%m%d)

# 3. 拉取最新代码
git pull origin main

# 4. 激活虚拟环境
source venv/bin/activate

# 5. 更新依赖
pip install -r requirements.txt --upgrade

# 6. 重启服务
sudo systemctl restart stock-analysis

# 7. 验证更新
sudo systemctl status stock-analysis
tail -f logs/app.log
```

## 📋 备份策略

### 数据库备份

```bash
# 创建备份脚本
sudo vim /opt/stock-analysis/backup.sh
```

**备份脚本内容**：

```bash
#!/bin/bash
BACKUP_DIR="/opt/backups/stock-analysis"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="stock_analysis"
DB_USER="YOUR_DB_USERNAME"
DB_PASS="YOUR_SECURE_PASSWORD"

# 创建备份目录
mkdir -p $BACKUP_DIR

# 备份数据库
mysqldump -u $DB_USER -p$DB_PASS $DB_NAME | gzip > $BACKUP_DIR/db_backup_$DATE.sql.gz

# 备份配置文件
cp /opt/stock-analysis/config.yaml $BACKUP_DIR/config_$DATE.yaml

# 删除30天前的备份
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete
find $BACKUP_DIR -name "*.yaml" -mtime +30 -delete

echo "Backup completed: $DATE"
```

```bash
# 设置执行权限
chmod +x /opt/stock-analysis/backup.sh

# 添加到crontab（每天凌晨2点执行）
crontab -e
# 添加以下行：
0 2 * * * /opt/stock-analysis/backup.sh >> /opt/stock-analysis/logs/backup.log 2>&1
```

## 📊 监控和维护

### 日志管理

```bash
# 查看实时日志
tail -f /opt/stock-analysis/logs/app.log

# 查看错误日志
grep ERROR /opt/stock-analysis/logs/app.log

# 日志轮转（logrotate）
sudo vim /etc/logrotate.d/stock-analysis
```

**Logrotate配置**：

```
/opt/stock-analysis/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 YOUR_USERNAME YOUR_USERNAME
    sharedscripts
    postrotate
        systemctl reload stock-analysis > /dev/null 2>&1 || true
    endscript
}
```

### 性能监控

```bash
# 监控CPU和内存使用
top -p $(cat /opt/stock-analysis/.stock_app.pid)

# 监控磁盘使用
df -h /opt/stock-analysis

# 监控数据库大小
mysql -u YOUR_DB_USERNAME -p -e "SELECT table_schema AS 'Database',
    ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'Size (MB)' 
    FROM information_schema.tables 
    WHERE table_schema = 'stock_analysis' 
    GROUP BY table_schema;"
```

## 🔒 安全建议

1. **修改默认密码**: 首次登录后立即修改管理员密码
2. **数据库安全**: 使用强密码，限制数据库访问权限
3. **防火墙配置**: 只开放必要的端口
4. **定期更新**: 及时更新系统和应用依赖
5. **备份策略**: 定期备份数据库和配置文件
6. **SSL证书**: 生产环境建议使用HTTPS
7. **日志审计**: 定期检查日志文件，发现异常及时处理

## 🔧 故障排查

### 服务无法启动

```bash
# 查看详细错误信息
sudo journalctl -u stock-analysis -n 50

# 检查配置文件
python -c "import yaml; yaml.safe_load(open('config.yaml'))"

# 检查数据库连接
mysql -u stock_user -p stock_analysis -e "SELECT 1;"

# 检查端口占用
sudo netstat -tlnp | grep -E '5000|8000'
```

### 数据库连接失败

```bash
# 检查MySQL服务
sudo systemctl status mysql

# 检查数据库用户权限
mysql -u root -p -e "SHOW GRANTS FOR 'YOUR_DB_USERNAME'@'localhost';"

# 测试连接
mysql -u YOUR_DB_USERNAME -p stock_analysis
```

### 性能问题

```bash
# 检查数据库索引
mysql -u YOUR_DB_USERNAME -p stock_analysis -e "SHOW INDEX FROM stocks;"

# 优化数据库
mysql -u YOUR_DB_USERNAME -p stock_analysis -e "OPTIMIZE TABLE stocks, market_data;"

# 检查慢查询日志
sudo tail -f /var/log/mysql/mysql-slow.log
```

## 🚀 扩展部署

### 多服务器部署

对于高可用部署，可以考虑：

1. **数据库分离**: 将MySQL部署到独立服务器
2. **负载均衡**: 使用Nginx或HAProxy进行负载均衡
3. **Redis缓存**: 添加Redis缓存层提升性能
4. **容器化部署**: 使用Docker/Kubernetes进行容器化部署

### Docker部署（可选）

```bash
# 创建Dockerfile
cat > Dockerfile << 'EOF'
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000 8000

CMD ["python", "main.py", "start", "--foreground"]
EOF

# 构建镜像
docker build -t stock-analysis:latest .

# 运行容器
docker run -d \
  --name stock-analysis \
  -p 5000:5000 \
  -p 8000:8000 \
  -v /opt/stock-analysis/config.yaml:/app/config.yaml \
  -v /opt/stock-analysis/logs:/app/logs \
  --restart unless-stopped \
  stock-analysis:latest
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
    token: YOUR_TUSHARE_TOKEN_HERE  # Tushare Token（请替换为实际token）

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
    username: YOUR_DB_USERNAME
    password: YOUR_DB_PASSWORD
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

### 配置项说明

#### 数据源配置
- `default`: 默认使用的数据源（akshare 或 tushare）
- `akshare.enabled`: 是否启用Akshare数据源
- `tushare.enabled`: 是否启用Tushare数据源
- `tushare.token`: Tushare API Token（需要注册获取）

#### API频率控制
- `min_delay`: 每次API请求的最小延迟时间（秒）
- `max_delay`: 每次API请求的最大延迟时间（秒）
- `max_retries`: API请求失败时的最大重试次数

#### 数据库配置
- `type`: 数据库类型（目前支持 mysql）
- `mysql.host`: MySQL服务器地址
- `mysql.port`: MySQL服务器端口
- `mysql.username`: 数据库用户名
- `mysql.password`: 数据库密码
- `mysql.database`: 数据库名称

#### 服务器配置
- `api.host`: API服务器监听地址（0.0.0.0 表示监听所有网卡）
- `api.port`: API服务器端口
- `api.debug`: 是否启用调试模式（生产环境应设为 false）
- `web.host`: Web服务器监听地址
- `web.port`: Web服务器端口
- `web.debug`: 是否启用调试模式

#### 调度任务配置
- `scheduler.enabled`: 是否启用定时任务
- `update_stock_list.hour`: 更新股票列表的小时（24小时制）
- `update_stock_list.minute`: 更新股票列表的分钟
- `update_market_data.hour`: 更新行情数据的小时
- `update_market_data.minute`: 更新行情数据的分钟

#### 日志配置
- `logging.level`: 日志级别（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- `logging.file`: 日志文件路径
- `logging.max_size`: 单个日志文件最大大小（字节）
- `logging.backup_count`: 保留的日志文件数量

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

**Q: 后台运行和前台运行有什么区别？**

A: 
- **后台运行**：服务在后台运行，不会占用终端窗口，适合生产环境
- **前台运行**：服务在终端窗口运行，可以实时查看日志，适合开发环境

### 数据导入

**Q: 数据导入失败怎么办？**
- 检查网络连接
- 检查数据源配置
- 查看日志文件 `logs/app.log`
- 确认服务已启动：`python main.py status`

**Q: API请求被限制怎么办？**
- 系统已内置频率控制机制
- 可调整 `config.yaml` 中的 `api_rate_limit` 配置

### Web界面

**Q: Web界面无法访问？**
- 确认API服务器已启动：`python main.py status`
- 检查端口是否被占用
- 确认防火墙设置

### 性能优化

**Q: 策略执行缓慢？**
- 检查数据库索引是否创建
- 考虑增加系统内存
- 优化策略条件

---

更多问题请参考主文档 [README.md](README.md) 或提交 Issue。
