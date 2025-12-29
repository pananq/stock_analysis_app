# SSL 证书配置指南

本文档详细说明如何为股票分析系统配置 SSL 证书，确保 HTTPS 安全访问。

## 目录

- [方案选择](#方案选择)
- [方案一：使用 Let's Encrypt 免费证书 + Nginx（推荐生产环境）](#方案一使用-lets-encrypt-免费证书--nginx推荐生产环境)
- [方案二：使用自签名证书 + Flask 内置 SSL（开发测试）](#方案二使用自签名证书--flask-内置-ssl开发测试)
- [方案三：使用商业 SSL 证书](#方案三使用商业-ssl-证书)
- [证书续期与管理](#证书续期与管理)
- [故障排查](#故障排查)

---

## 方案选择

根据使用场景选择合适的方案：

| 方案 | 适用场景 | 优点 | 缺点 |
|------|---------|------|------|
| **Let's Encrypt + Nginx** | 生产环境、公网访问 | 免费、自动续期、高性能 | 需要配置 Nginx |
| **自签名证书 + Flask** | 开发测试、内网访问 | 配置简单、无需外部依赖 | 浏览器警告、不被信任 |
| **商业 SSL 证书** | 企业级应用、高安全要求 | 高信任度、支持多种验证 | 需要付费 |

**推荐**: 生产环境使用 **Let's Encrypt + Nginx**，开发测试使用 **自签名证书**。

---

## 方案一：使用 Let's Encrypt 免费证书 + Nginx（推荐生产环境）

### 1.1 系统要求

- 域名（如：stock-analysis.yourdomain.com）
- 服务器已安装 Nginx
- 服务器公网 IP 已绑定域名
- 服务器开放 80 和 443 端口

### 1.2 安装 Nginx

#### CentOS/RHEL

```bash
# 安装 EPEL 源
sudo yum install epel-release -y

# 安装 Nginx
sudo yum install nginx -y

# 启动 Nginx
sudo systemctl start nginx
sudo systemctl enable nginx
```

#### Ubuntu/Debian

```bash
# 更新包列表
sudo apt update

# 安装 Nginx
sudo apt install nginx -y

# 启动 Nginx
sudo systemctl start nginx
sudo systemctl enable nginx
```

### 1.3 安装 Certbot

#### CentOS/RHEL 7/8

```bash
# 安装 EPEL 源
sudo yum install epel-release -y

# 安装 Certbot
sudo yum install certbot python3-certbot-nginx -y
```

#### CentOS/RHEL 9 / Rocky Linux 9

```bash
# 启用 EPEL 模块
sudo dnf config-manager --set-enabled crb

# 安装 EPEL
sudo dnf install epel-release -y

# 安装 Certbot
sudo dnf install certbot python3-certbot-nginx -y
```

#### Ubuntu/Debian

```bash
# 安装 Certbot
sudo apt install certbot python3-certbot-nginx -y
```

### 1.4 配置 Nginx 反向代理

创建 Nginx 配置文件：

```bash
sudo vi /etc/nginx/conf.d/stock-analysis.conf
```

添加以下配置：

```nginx
# API 服务器配置 (端口 5000)
upstream api_backend {
    server 127.0.0.1:5000;
    keepalive 32;
}

# Web 服务器配置 (端口 8000)
upstream web_backend {
    server 127.0.0.1:8000;
    keepalive 32;
}

# HTTPS 服务器配置
server {
    listen 80;
    listen [::]:80;
    server_name stock-analysis.yourdomain.com;  # 替换为您的域名
    
    # 重定向到 HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name stock-analysis.yourdomain.com;  # 替换为您的域名
    
    # SSL 证书路径（Certbot 会自动配置）
    # ssl_certificate /etc/letsencrypt/live/stock-analysis.yourdomain.com/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/stock-analysis.yourdomain.com/privkey.pem;
    
    # SSL 安全配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_session_tickets off;
    
    # HSTS (可选，强制使用 HTTPS)
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    
    # 安全头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # 日志配置
    access_log /var/log/nginx/stock-analysis-access.log;
    error_log /var/log/nginx/stock-analysis-error.log;
    
    # 客户端最大请求体大小
    client_max_body_size 10M;
    
    # 超时配置
    proxy_connect_timeout 300s;
    proxy_send_timeout 300s;
    proxy_read_timeout 300s;
    
    # API 请求代理
    location /api/ {
        proxy_pass http://api_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_buffering off;
    }
    
    # Web 请求代理
    location / {
        proxy_pass http://web_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
    
    # 健康检查端点
    location /health {
        proxy_pass http://api_backend/health;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        access_log off;
    }
}
```

### 1.5 测试 Nginx 配置

```bash
# 测试配置文件语法
sudo nginx -t

# 如果测试通过，重新加载 Nginx
sudo systemctl reload nginx
```

### 1.6 获取 SSL 证书

运行 Certbot 自动配置：

```bash
# 自动配置 Nginx 并获取证书
sudo certbot --nginx -d stock-analysis.yourdomain.com

# 或指定多个域名
sudo certbot --nginx -d stock-analysis.yourdomain.com -d www.stock-analysis.yourdomain.com
```

Certbot 会提示：
1. 输入邮箱地址（用于证书到期提醒）
2. 同意服务条款
3. 选择是否共享邮箱
4. 自动配置 Nginx SSL

### 1.7 验证 SSL 证书

```bash
# 检查证书状态
sudo certbot certificates

# 访问 HTTPS 网站
curl -I https://stock-analysis.yourdomain.com
```

访问 `https://stock-analysis.yourdomain.com` 查看网站是否正常工作。

### 1.8 配置防火墙

确保防火墙允许 HTTPS 流量：

#### CentOS/RHEL (firewalld)

```bash
# 开放 HTTPS 端口
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --reload

# 查看防火墙状态
sudo firewall-cmd --list-all
```

#### Ubuntu (UFW)

```bash
# 允许 HTTPS
sudo ufw allow 'Nginx Full'
sudo ufw reload
```

### 1.9 自动续期配置

Certbot 会自动配置续期任务：

```bash
# 检查自动续期任务
sudo systemctl status certbot.timer

# 手动测试续期
sudo certbot renew --dry-run
```

默认情况下，证书每天自动检查两次，快到期时自动续期。

---

## 方案二：使用自签名证书 + Flask 内置 SSL（开发测试）

### 2.1 生成自签名证书

```bash
# 创建证书目录
mkdir -p /data/home/aaronpan/stock-analysis-app/ssl

# 生成私钥
openssl genrsa -out ssl/server.key 2048

# 生成证书签名请求 (CSR)
openssl req -new -key ssl/server.key -out ssl/server.csr \
  -subj "/C=CN/ST=Beijing/L=Beijing/O=YourCompany/OU=IT/CN=localhost"

# 生成自签名证书（有效期 365 天）
openssl x509 -req -days 365 -in ssl/server.csr -signkey ssl/server.key -out ssl/server.crt

# 设置权限
chmod 600 ssl/server.key
chmod 644 ssl/server.crt
```

### 2.2 修改 Flask 应用支持 SSL

编辑 [main.py](main.py)，添加 SSL 支持：

```python
# 在 run_api_server 函数中
def run_api_server():
    """运行API服务器"""
    from app.api import create_app
    from app.scheduler import get_task_scheduler
    
    logger = get_logger(__name__)
    config = get_config()
    
    try:
        app = create_app(config)
        scheduler = get_task_scheduler()
        
        # 添加定时任务
        scheduler.add_daily_stock_update_job(hour=18, minute=0)
        scheduler.add_daily_market_data_update_job(hour=18, minute=30)
        scheduler.add_daily_strategy_execution_job(hour=19, minute=0)
        scheduler.add_periodic_health_check_job(interval_minutes=30)
        
        scheduler.start()
        
        # 获取API配置
        api_config = config.get('api', {})
        host = api_config.get('host', '0.0.0.0')
        port = api_config.get('port', 5000)
        debug = api_config.get('debug', False)
        
        # SSL 配置
        ssl_context = None
        if api_config.get('ssl_enabled', False):
            ssl_context = (
                api_config.get('ssl_cert', 'ssl/server.crt'),
                api_config.get('ssl_key', 'ssl/server.key')
            )
            logger.info(f"SSL 已启用，证书: {ssl_context[0]}")
        
        logger.info(f"API服务器启动: {'https' if ssl_context else 'http'}://{host}:{port}")
        
        # 启动Flask应用
        app.run(
            host=host,
            port=port,
            debug=debug,
            ssl_context=ssl_context,
            use_reloader=False
        )
        
    except KeyboardInterrupt:
        logger.info("\n收到中断信号，正在关闭API服务器...")
        try:
            scheduler = get_task_scheduler()
            scheduler.shutdown(wait=True)
            logger.info("调度器已关闭")
        except:
            pass
        logger.info("API服务器已关闭")


# 在 run_web_server 函数中
def run_web_server():
    """运行Web服务器"""
    from app.web import create_web_app
    
    logger = get_logger(__name__)
    config = get_config()
    
    try:
        app = create_web_app(config)
        
        # 获取Web配置
        web_config = config.get('web', {})
        host = web_config.get('host', '0.0.0.0')
        port = web_config.get('port', 8000)
        debug = web_config.get('debug', False)
        
        # SSL 配置
        ssl_context = None
        if web_config.get('ssl_enabled', False):
            ssl_context = (
                web_config.get('ssl_cert', 'ssl/server.crt'),
                web_config.get('ssl_key', 'ssl/server.key')
            )
            logger.info(f"SSL 已启用，证书: {ssl_context[0]}")
        
        logger.info(f"Web服务器启动: {'https' if ssl_context else 'http'}://{host}:{port}")
        
        # 启动Flask应用
        app.run(
            host=host,
            port=port,
            debug=debug,
            ssl_context=ssl_context
        )
        
    except KeyboardInterrupt:
        logger.info("\n收到中断信号，正在关闭Web服务器...")
        logger.info("Web服务器已关闭")
```

### 2.3 更新配置文件

编辑配置文件（如 `config.yaml` 或 `config/config.yaml`），添加 SSL 配置：

```yaml
api:
  host: 0.0.0.0
  port: 5000
  debug: false
  ssl_enabled: true
  ssl_cert: /data/home/aaronpan/stock-analysis-app/ssl/server.crt
  ssl_key: /data/home/aaronpan/stock-analysis-app/ssl/server.key

web:
  host: 0.0.0.0
  port: 8000
  debug: false
  ssl_enabled: true
  ssl_cert: /data/home/aaronpan/stock-analysis-app/ssl/server.crt
  ssl_key: /data/home/aaronpan/stock-analysis-app/ssl/server.key
```

### 2.4 启动服务

```bash
# 前台启动（测试）
python main.py start --foreground

# 后台启动
python main.py start

# 访问
# API: https://localhost:5000
# Web: https://localhost:8000
```

### 2.5 浏览器警告处理

由于是自签名证书，浏览器会显示安全警告。处理方法：

1. 点击"高级" → "继续访问"
2. 或手动添加证书信任：
   - Chrome: 设置 → 隐私和安全 → 安全 → 管理证书 → 导入
   - Firefox: 首选项 → 隐私与安全 → 证书 → 查看证书 → 导入

---

## 方案三：使用商业 SSL 证书

### 3.1 购买 SSL 证书

从受信任的证书颁发机构（CA）购买：
- DigiCert
- GlobalSign
- Sectigo
- Let's Encrypt（免费）

### 3.2 生成 CSR 文件

```bash
# 创建私钥（4096 位，更安全）
openssl genrsa -out ssl/yourdomain.com.key 4096

# 生成 CSR
openssl req -new -key ssl/yourdomain.com.key -out ssl/yourdomain.com.csr

# 填写证书信息
Country Name (2 letter code): CN
State or Province Name: Beijing
Locality Name: Beijing
Organization Name: Your Company
Organizational Unit Name: IT
Common Name: stock-analysis.yourdomain.com  # 重要：填写域名
Email Address: admin@yourdomain.com

# 跳过密码保护（生产环境推荐）
A challenge password: [回车]
An optional company name: [回车]
```

### 3.3 提交 CSR 到证书颁发机构

1. 将 `ssl/yourdomain.com.csr` 内容复制到 CA 的网站
2. 完成域名验证（DNS 或文件验证）
3. 下载证书文件

### 3.4 安装证书

将下载的证书文件和 CA 中间证书放到 `ssl` 目录：

```bash
# 假设收到的文件：
# - yourdomain.com.crt（服务器证书）
# - intermediate.crt（中间证书）
# - yourdomain.com.key（私钥，已生成）

# 合并服务器证书和中间证书（按照 CA 提供的顺序）
cat ssl/yourdomain.com.crt ssl/intermediate.crt > ssl/ssl-bundle.crt
```

### 3.5 配置 Nginx

```nginx
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name stock-analysis.yourdomain.com;
    
    # SSL 证书
    ssl_certificate /path/to/ssl/ssl-bundle.crt;
    ssl_certificate_key /path/to/ssl/yourdomain.com.key;
    
    # SSL 安全配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # 其他配置...
}
```

### 3.6 测试配置

```bash
# 测试 Nginx 配置
sudo nginx -t

# 重新加载 Nginx
sudo systemctl reload nginx

# 测试 SSL 连接
openssl s_client -connect stock-analysis.yourdomain.com:443
```

---

## 证书续期与管理

### Let's Encrypt 自动续期

```bash
# 查看证书到期时间
sudo certbot certificates

# 手动续期
sudo certbot renew

# 测试续期（不实际续期）
sudo certbot renew --dry-run

# 查看自动续期任务
sudo systemctl status certbot.timer
```

### 自签名证书续期

```bash
# 生成新证书
openssl genrsa -out ssl/server.key 2048
openssl req -new -key ssl/server.key -out ssl/server.csr \
  -subj "/C=CN/ST=Beijing/L=Beijing/O=YourCompany/OU=IT/CN=localhost"
openssl x509 -req -days 365 -in ssl/server.csr -signkey ssl/server.key -out ssl/server.crt

# 重启服务
python main.py restart
```

### 商业证书续期

1. 购买新证书
2. 生成新的 CSR（或使用原 CSR）
3. 提交到 CA
4. 替换旧证书文件
5. 重启 Nginx

---

## 故障排查

### 1. 证书验证失败

**问题**: 浏览器显示证书无效

**解决方案**:
```bash
# 检查证书链
openssl s_client -connect yourdomain.com:443 -showcerts

# 检查证书有效期
openssl x509 -in ssl/server.crt -noout -dates

# 检查证书与域名匹配
openssl x509 -in ssl/server.crt -noout -subject | grep CN=
```

### 2. Nginx 启动失败

**问题**: Nginx 无法启动

**解决方案**:
```bash
# 查看错误日志
sudo tail -f /var/log/nginx/error.log

# 测试配置文件
sudo nginx -t

# 检查证书文件权限
ls -la /etc/letsencrypt/live/yourdomain.com/
```

### 3. SSL 握手失败

**问题**: 无法建立 SSL 连接

**解决方案**:
```bash
# 检查端口是否开放
sudo netstat -tlnp | grep 443

# 检查防火墙
sudo firewall-cmd --list-ports

# 测试 SSL 连接
openssl s_client -connect localhost:443
```

### 4. 证书过期

**问题**: 证书已过期

**解决方案**:
```bash
# Let's Encrypt
sudo certbot renew

# 商业证书
# 重新申请新证书并替换

# 自签名证书
# 按步骤重新生成
```

### 5. 混合内容警告

**问题**: HTTPS 页面包含 HTTP 资源

**解决方案**:
- 检查 HTML 中的资源链接，确保都使用 HTTPS
- 使用相对路径（如 `//cdn.example.com/js/app.js`）
- 配置 CSP (Content Security Policy)

### 6. 性能问题

**问题**: HTTPS 访问变慢

**解决方案**:
```nginx
# 启用 HTTP/2
listen 443 ssl http2;

# 启用 SSL 会话缓存
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 10m;

# 启用 OCSP Stapling
ssl_stapling on;
ssl_stapling_verify on;
ssl_trusted_certificate /path/to/chain.pem;
```

---

## 安全最佳实践

### 1. 使用强加密

```nginx
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256';
ssl_prefer_server_ciphers off;
```

### 2. 启用 HSTS

```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
```

### 3. 保护私钥

```bash
# 设置严格的文件权限
chmod 600 /path/to/ssl/*.key
chown root:root /path/to/ssl/*.key
```

### 4. 定期更新证书

- 设置证书到期提醒
- 配置自动续期
- 定期检查证书状态

### 5. 监控 SSL 状态

使用工具监控 SSL 证书：
- SSL Labs Server Test: https://www.ssllabs.com/ssltest/
- Certbot 自动续期日志
- Nginx 访问日志

---

## 快速开始脚本

创建自动化脚本 `setup_ssl.sh`：

```bash
#!/bin/bash
# SSL 配置快速启动脚本

set -e

# 配置变量
DOMAIN="stock-analysis.yourdomain.com"
EMAIL="admin@yourdomain.com"
PROJECT_DIR="/data/home/aaronpan/stock-analysis-app"

echo "================================================"
echo "SSL 证书配置脚本"
echo "================================================"

# 检查是否为 root
if [ "$EUID" -ne 0 ]; then 
    echo "请使用 sudo 运行此脚本"
    exit 1
fi

# 选择方案
echo "请选择 SSL 配置方案:"
echo "1. Let's Encrypt + Nginx (推荐生产环境)"
echo "2. 自签名证书 + Flask (开发测试)"
read -p "请输入选项 (1/2): " choice

case $choice in
    1)
        echo "配置 Let's Encrypt + Nginx..."
        
        # 安装 Nginx
        yum install -y nginx || apt install -y nginx
        
        # 安装 Certbot
        yum install -y certbot python3-certbot-nginx || apt install -y certbot python3-certbot-nginx
        
        # 配置 Nginx
        cat > /etc/nginx/conf.d/stock-analysis.conf << EOF
upstream api_backend {
    server 127.0.0.1:5000;
    keepalive 32;
}

upstream web_backend {
    server 127.0.0.1:8000;
    keepalive 32;
}

server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN;
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name $DOMAIN;
    
    location /api/ {
        proxy_pass http://api_backend;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    location / {
        proxy_pass http://web_backend;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
        
        # 测试并重启 Nginx
        nginx -t && systemctl reload nginx
        
        # 获取证书
        certbot --nginx -d $DOMAIN --email $EMAIL --agree-tos --no-eff-email
        
        echo "✓ Let's Encrypt 证书配置完成"
        echo "  访问: https://$DOMAIN"
        ;;
    
    2)
        echo "配置自签名证书..."
        
        # 创建证书目录
        mkdir -p $PROJECT_DIR/ssl
        cd $PROJECT_DIR/ssl
        
        # 生成证书
        openssl genrsa -out server.key 2048
        openssl req -new -key server.key -out server.csr \
            -subj "/C=CN/ST=Beijing/L=Beijing/O=YourCompany/OU=IT/CN=localhost"
        openssl x509 -req -days 365 -in server.csr -signkey server.key -out server.crt
        
        chmod 600 server.key
        chmod 644 server.crt
        
        echo "✓ 自签名证书生成完成"
        echo "  证书文件: $PROJECT_DIR/ssl/server.crt"
        echo "  私钥文件: $PROJECT_DIR/ssl/server.key"
        echo ""
        echo "请更新配置文件启用 SSL:"
        echo "  api:"
        echo "    ssl_enabled: true"
        echo "    ssl_cert: $PROJECT_DIR/ssl/server.crt"
        echo "    ssl_key: $PROJECT_DIR/ssl/server.key"
        ;;
    
    *)
        echo "无效的选项"
        exit 1
        ;;
esac

echo "================================================"
echo "配置完成"
echo "================================================"
```

使用脚本：

```bash
# 赋予执行权限
chmod +x setup_ssl.sh

# 运行脚本
sudo ./setup_ssl.sh
```

---

## 总结

| 方案 | 推荐场景 | 难度 | 成本 | 维护 |
|------|---------|------|------|------|
| **Let's Encrypt + Nginx** | 生产环境 | 中等 | 免费 | 自动 |
| **自签名 + Flask** | 开发测试 | 简单 | 免费 | 手动 |
| **商业证书** | 企业应用 | 中等 | 付费 | 手动 |

**推荐流程**:
1. 开发测试：使用自签名证书快速验证
2. 生产部署：使用 Let's Encrypt + Nginx 实现自动化
3. 如需更高信任度：购买商业证书

配置完成后，使用 SSL Labs 测试网站安全等级：https://www.ssllabs.com/ssltest/
