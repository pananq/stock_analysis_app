# Gunicorn 生产环境部署指南

本指南介绍如何在生产环境中使用 Gunicorn 部署股票分析系统。

## 目录结构

```
stock-analysis-app/
├── gunicorn_config.py      # Gunicorn 配置文件
├── run_gunicorn.py         # Gunicorn 启动脚本
├── stock-api.service       # API 服务 systemd 配置
├── stock-web.service       # Web 服务 systemd 配置
├── deploy_gunicorn.sh      # 自动部署脚本
└── requirements.txt        # 包含 gunicorn 依赖
```

## 快速开始

### 方法一：使用自动部署脚本（推荐）

1. **运行部署脚本**（需要 sudo 权限）：

```bash
cd /data/home/aaronpan/stock-analysis-app
sudo ./deploy_gunicorn.sh
```

该脚本会自动完成以下操作：
- 安装 Gunicorn
- 创建日志目录
- 部署 systemd 服务文件
- 启用并启动服务

### 方法二：手动部署

1. **安装 Gunicorn**：

```bash
source venv/bin/activate
pip install gunicorn==21.2.0
```

2. **部署 systemd 服务**：

```bash
# 复制服务文件到 systemd 目录
sudo cp stock-api.service /etc/systemd/system/
sudo cp stock-web.service /etc/systemd/system/

# 重新加载 systemd 配置
sudo systemctl daemon-reload

# 启用服务（开机自启）
sudo systemctl enable stock-api.service
sudo systemctl enable stock-web.service

# 启动服务
sudo systemctl start stock-api.service
sudo systemctl start stock-web.service
```

## 服务管理命令

### 查看服务状态

```bash
# API 服务
sudo systemctl status stock-api

# Web 服务
sudo systemctl status stock-web
```

### 启动/停止/重启服务

```bash
# 启动
sudo systemctl start stock-api
sudo systemctl start stock-web

# 停止
sudo systemctl stop stock-api
sudo systemctl stop stock-web

# 重启
sudo systemctl restart stock-api
sudo systemctl restart stock-web

# 重新加载配置（不中断服务）
sudo systemctl reload stock-api
sudo systemctl reload stock-web
```

### 查看日志

```bash
# 实时查看日志
sudo journalctl -u stock-api -f
sudo journalctl -u stock-web -f

# 查看最近 100 行日志
sudo journalctl -u stock-api -n 100
sudo journalctl -u stock-web -n 100

# 查看今天开始的日志
sudo journalctl -u stock-api --since today
sudo journalctl -u stock-web --since today
```

## 测试 Gunicorn 配置

### 使用启动脚本测试

```bash
# 测试 API 服务（前台运行）
python run_gunicorn.py --service api

# 测试 Web 服务（前台运行）
python run_gunicorn.py --service web
```

### 直接使用 Gunicorn 命令

```bash
# 启动 API 服务
gunicorn --config gunicorn_config.py app.api.app:create_app()

# 启动 Web 服务
gunicorn --config gunicorn_config.py --bind 0.0.0.0:8000 app.web.app:create_web_app()
```

## 配置说明

### Gunicorn 配置文件 (gunicorn_config.py)

主要配置项：

```python
# 服务器地址
bind = "0.0.0.0:5000"

# 工作进程数量
workers = multiprocessing.cpu_count() * 2 + 1

# 工作模式
worker_class = "sync"

# 超时设置
timeout = 30
keepalive = 2

# 请求限制（防止内存泄漏）
max_requests = 1000
max_requests_jitter = 50

# 日志级别
loglevel = "info"
```

### 优化建议

根据服务器资源调整以下参数：

1. **workers（工作进程数）**：
   - 公式：`(2 × CPU核心数) + 1`
   - 例如：4 核 CPU → `workers = 9`

2. **worker_connections（连接数）**：
   - 默认：1000
   - 可根据服务器内存调整

3. **max_requests**：
   - 建议值：1000-5000
   - 防止内存泄漏，定期重启 worker

## 常见问题

### 1. 端口被占用

检查端口占用：

```bash
# 检查 5000 端口
sudo lsof -i :5000

# 检查 8000 端口
sudo lsof -i :8000
```

### 2. 权限问题

确保 systemd 服务文件中的用户和组设置正确：

```ini
User=aaronpan
Group=aaronpan
```

### 3. 服务无法启动

查看详细日志：

```bash
sudo journalctl -u stock-api -xe
sudo journalctl -u stock-web -xe
```

### 4. 配置热重载

修改 `gunicorn_config.py` 后，执行：

```bash
sudo systemctl daemon-reload
sudo systemctl restart stock-api
sudo systemctl restart stock-web
```

## 性能监控

### 使用 htop 监控进程

```bash
htop
```

查找 `gunicorn: master` 和 `gunicorn: worker` 进程

### 查看资源使用情况

```bash
# CPU 和内存
sudo systemctl status stock-api

# 详细统计
sudo systemd-cgtop
```

## 安全建议

1. **启用 HTTPS**：
   - 使用 Nginx 或 Caddy 作为反向代理
   - 配置 SSL 证书

2. **防火墙设置**：
   ```bash
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw enable
   ```

3. **限制访问**：
   - 使用 iptables 或云服务商的安全组
   - 限制 API 访问 IP

## 反向代理配置（可选）

### Nginx 配置示例

```nginx
# API 服务器
upstream stock_api {
    server 127.0.0.1:5000;
}

server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://stock_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Web 服务器
upstream stock_web {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name www.yourdomain.com;

    location / {
        proxy_pass http://stock_web;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 备份与恢复

### 备份配置文件

```bash
tar -czf gunicorn-config-backup.tar.gz \
    gunicorn_config.py \
    stock-api.service \
    stock-web.service
```

### 恢复配置

```bash
tar -xzf gunicorn-config-backup.tar.gz
sudo systemctl daemon-reload
sudo systemctl restart stock-api
sudo systemctl restart stock-web
```

## 从开发环境迁移

如果您之前使用 Flask 开发服务器：

1. **停止开发服务器**：
   ```bash
   python main.py stop
   ```

2. **安装 Gunicorn**：
   ```bash
   pip install gunicorn==21.2.0
   ```

3. **使用 systemd 管理**：
   ```bash
   sudo ./deploy_gunicorn.sh
   ```

## 更新 Gunicorn

```bash
# 更新到最新版本
source venv/bin/activate
pip install --upgrade gunicorn

# 或者更新到特定版本
pip install gunicorn==21.2.0

# 重启服务
sudo systemctl restart stock-api
sudo systemctl restart stock-web
```

## 总结

✅ **已完成配置**：
- Gunicorn 配置文件
- systemd 服务文件
- 自动部署脚本
- 启动脚本

🚀 **下一步**：
1. 运行 `sudo ./deploy_gunicorn.sh` 部署服务
2. 使用 `sudo systemctl status stock-api` 检查服务状态
3. 访问 `http://your-server:5000` 和 `http://your-server:8000` 测试服务
