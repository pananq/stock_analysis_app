#!/bin/bash
###########################################################
# SSL证书配置快速脚本
# 用于股票分析系统的SSL证书自动化配置
###########################################################

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置变量（可修改）
DOMAIN="stock-analysis.example.com"
EMAIL="admin@example.com"
PROJECT_DIR="/data/home/aaronpan/stock-analysis-app"
NGINX_CONF_DIR="/etc/nginx/conf.d"

# 检测操作系统
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    echo -e "${RED}无法检测操作系统${NC}"
    exit 1
fi

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否为root用户
check_root() {
    if [ "$EUID" -ne 0 ]; then 
        print_error "请使用 sudo 运行此脚本"
        exit 1
    fi
}

# 显示菜单
show_menu() {
    echo ""
    echo "================================================"
    echo -e "${GREEN}SSL证书配置工具${NC}"
    echo "================================================"
    echo ""
    echo "请选择SSL配置方案:"
    echo ""
    echo "  1) Let's Encrypt + Nginx (推荐生产环境)"
    echo "     - 免费证书"
    echo "     - 自动续期"
    echo "     - 需要域名"
    echo ""
    echo "  2) 自签名证书 + Flask (开发测试)"
    echo "     - 快速配置"
    echo "     - 内网访问"
    echo "     - 浏览器警告"
    echo ""
    echo "  3) 只生成自签名证书"
    echo "     - 不修改应用配置"
    echo "     - 仅生成证书文件"
    echo ""
    echo "  4) 检查SSL状态"
    echo ""
    echo "  0) 退出"
    echo ""
    echo "================================================"
}

# 安装Nginx
install_nginx() {
    print_info "检查Nginx是否已安装..."
    
    if command -v nginx &> /dev/null; then
        print_success "Nginx已安装"
        return 0
    fi
    
    print_info "正在安装Nginx..."
    
    case $OS in
        centos|rhel|rocky|almalinux)
            yum install -y epel-release
            yum install -y nginx
            ;;
        ubuntu|debian)
            apt update
            apt install -y nginx
            ;;
        fedora)
            dnf install -y nginx
            ;;
        *)
            print_error "不支持的操作系统: $OS"
            exit 1
            ;;
    esac
    
    # 启动Nginx
    systemctl start nginx
    systemctl enable nginx
    
    print_success "Nginx安装完成"
}

# 安装Certbot
install_certbot() {
    print_info "检查Certbot是否已安装..."
    
    if command -v certbot &> /dev/null; then
        print_success "Certbot已安装"
        return 0
    fi
    
    print_info "正在安装Certbot..."
    
    case $OS in
        centos|rhel)
            if [ "$VERSION_ID" = "7" ]; then
                yum install -y epel-release
                yum install -y certbot python2-certbot-nginx
            else
                yum install -y epel-release
                yum install -y certbot python3-certbot-nginx
            fi
            ;;
        rocky|almalinux)
            dnf config-manager --set-enabled crb
            dnf install -y epel-release
            dnf install -y certbot python3-certbot-nginx
            ;;
        ubuntu|debian)
            apt install -y certbot python3-certbot-nginx
            ;;
        fedora)
            dnf install -y certbot python3-certbot-nginx
            ;;
        *)
            print_error "不支持的操作系统: $OS"
            exit 1
            ;;
    esac
    
    print_success "Certbot安装完成"
}

# 配置Nginx反向代理
configure_nginx() {
    local domain=$1
    
    print_info "配置Nginx反向代理..."
    
    # 创建配置文件
    cat > $NGINX_CONF_DIR/stock-analysis.conf << EOF
upstream api_backend {
    server 127.0.0.1:5000;
    keepalive 32;
}

upstream web_backend {
    server 127.0.0.1:8000;
    keepalive 32;
}

# HTTP 重定向到 HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name $domain;
    
    # 允许 Let's Encrypt 验证
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    # 其他请求重定向到 HTTPS
    location / {
        return 301 https://\$server_name\$request_uri;
    }
}

# HTTPS 服务器
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name $domain;
    
    # SSL 证书路径（Certbot 会自动配置）
    ssl_certificate /etc/letsencrypt/live/$domain/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$domain/privkey.pem;
    
    # SSL 安全配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_session_tickets off;
    
    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # 安全头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # 日志配置
    access_log /var/log/nginx/stock-analysis-access.log;
    error_log /var/log/nginx/stock-analysis-error.log;
    
    # 客户端配置
    client_max_body_size 10M;
    client_body_timeout 60s;
    
    # 超时配置
    proxy_connect_timeout 300s;
    proxy_send_timeout 300s;
    proxy_read_timeout 300s;
    
    # API 请求代理
    location /api/ {
        proxy_pass http://api_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        proxy_buffering off;
    }
    
    # Web 请求代理
    location / {
        proxy_pass http://web_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
    }
    
    # 健康检查
    location /health {
        proxy_pass http://api_backend/health;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        access_log off;
    }
}
EOF
    
    # 创建 certbot 验证目录
    mkdir -p /var/www/certbot
    
    # 测试配置
    print_info "测试Nginx配置..."
    if nginx -t; then
        print_success "Nginx配置测试通过"
        systemctl reload nginx
    else
        print_error "Nginx配置测试失败"
        exit 1
    fi
    
    print_success "Nginx配置完成"
}

# 配置防火墙
configure_firewall() {
    print_info "配置防火墙..."
    
    case $OS in
        centos|rhel|rocky|almalinux|fedora)
            if command -v firewall-cmd &> /dev/null; then
                firewall-cmd --permanent --add-service=http
                firewall-cmd --permanent --add-service=https
                firewall-cmd --reload
                print_success "Firewalld配置完成"
            else
                print_warning "未检测到firewalld，跳过防火墙配置"
            fi
            ;;
        ubuntu|debian)
            if command -v ufw &> /dev/null; then
                ufw allow 'Nginx Full'
                ufw reload
                print_success "UFW配置完成"
            else
                print_warning "未检测到UFW，跳过防火墙配置"
            fi
            ;;
        *)
            print_warning "不支持的防火墙配置"
            ;;
    esac
}

# 获取Let's Encrypt证书
get_letsencrypt_cert() {
    local domain=$1
    local email=$2
    
    print_info "准备获取Let's Encrypt证书..."
    print_warning "请确保："
    print_warning "  1. 域名 $domain 已正确解析到当前服务器"
    print_warning "  2. 服务器80和443端口可访问"
    print_warning "  3. 防火墙已开放相应端口"
    echo ""
    read -p "确认以上条件已满足？(y/n): " confirm
    
    if [ "$confirm" != "y" ]; then
        print_error "配置已取消"
        exit 1
    fi
    
    print_info "正在获取证书..."
    
    # 使用 certbot 自动配置
    certbot --nginx \
        -d $domain \
        --email $email \
        --agree-tos \
        --no-eff-email \
        --redirect
    
    if [ $? -eq 0 ]; then
        print_success "证书获取成功"
        
        # 检查自动续期
        print_info "检查自动续期配置..."
        systemctl status certbot.timer --no-pager
        
        print_info "测试证书续期..."
        certbot renew --dry-run
        
        print_success "Let's Encrypt配置完成"
    else
        print_error "证书获取失败"
        exit 1
    fi
}

# 生成自签名证书
generate_self_signed_cert() {
    local project_dir=$1
    local ssl_dir="$project_dir/ssl"
    
    print_info "生成自签名证书..."
    
    # 创建证书目录
    mkdir -p $ssl_dir
    
    # 生成私钥
    print_info "生成私钥..."
    openssl genrsa -out $ssl_dir/server.key 2048
    
    # 生成证书签名请求
    print_info "生成证书签名请求..."
    openssl req -new \
        -key $ssl_dir/server.key \
        -out $ssl_dir/server.csr \
        -subj "/C=CN/ST=Beijing/L=Beijing/O=YourCompany/OU=IT/CN=localhost"
    
    # 生成自签名证书（365天）
    print_info "生成自签名证书（有效期365天）..."
    openssl x509 -req \
        -days 365 \
        -in $ssl_dir/server.csr \
        -signkey $ssl_dir/server.key \
        -out $ssl_dir/server.crt
    
    # 设置权限
    chmod 600 $ssl_dir/server.key
    chmod 644 $ssl_dir/server.crt
    
    # 清理CSR文件
    rm -f $ssl_dir/server.csr
    
    print_success "自签名证书生成完成"
    echo ""
    echo "证书文件:"
    echo "  证书: $ssl_dir/server.crt"
    echo "  私钥: $ssl_dir/server.key"
}

# 更新应用配置
update_app_config() {
    local project_dir=$1
    local ssl_dir="$project_dir/ssl"
    
    print_info "更新应用配置..."
    
    # 查找配置文件
    local config_file=""
    if [ -f "$project_dir/config.yaml" ]; then
        config_file="$project_dir/config.yaml"
    elif [ -f "$project_dir/config/config.yaml" ]; then
        config_file="$project_dir/config/config.yaml"
    elif [ -f "$project_dir/config.yml" ]; then
        config_file="$project_dir/config.yml"
    else
        print_warning "未找到配置文件，请手动配置SSL"
        print_info "需要添加以下配置："
        echo ""
        echo "api:"
        echo "  ssl_enabled: true"
        echo "  ssl_cert: $ssl_dir/server.crt"
        echo "  ssl_key: $ssl_dir/server.key"
        echo ""
        echo "web:"
        echo "  ssl_enabled: true"
        echo "  ssl_cert: $ssl_dir/server.crt"
        echo "  ssl_key: $ssl_dir/server.key"
        return
    fi
    
    # 备份配置文件
    cp $config_file ${config_file}.backup.$(date +%Y%m%d_%H%M%S)
    print_info "已备份配置文件: ${config_file}.backup.*"
    
    # 提示用户手动编辑
    print_warning "请手动编辑配置文件 $config_file"
    print_info "添加以下配置："
    echo ""
    echo "api:"
    echo "  ssl_enabled: true"
    echo "  ssl_cert: $ssl_dir/server.crt"
    echo "  ssl_key: $ssl_dir/server.key"
    echo ""
    echo "web:"
    echo "  ssl_enabled: true"
    echo "  ssl_cert: $ssl_dir/server.crt"
    echo "  ssl_key: $ssl_dir/server.key"
    echo ""
    read -p "按回车键继续..."
}

# 检查SSL状态
check_ssl_status() {
    print_info "检查SSL状态..."
    echo ""
    
    # 检查Let's Encrypt证书
    if command -v certbot &> /dev/null; then
        print_info "Let's Encrypt 证书状态:"
        certbot certificates
        echo ""
    else
        print_warning "Certbot未安装"
    fi
    
    # 检查自签名证书
    if [ -f "$PROJECT_DIR/ssl/server.crt" ]; then
        print_info "自签名证书信息:"
        openssl x509 -in $PROJECT_DIR/ssl/server.crt -noout -subject -dates
        echo ""
    fi
    
    # 检查Nginx配置
    if command -v nginx &> /dev/null; then
        print_info "Nginx状态:"
        systemctl status nginx --no-pager -l
        echo ""
        
        print_info "Nginx配置:"
        nginx -T 2>/dev/null | grep -A 5 "ssl_certificate"
    fi
    
    # 检查端口
    print_info "端口监听状态:"
    netstat -tlnp | grep -E ':(80|443|5000|8000)\s' || ss -tlnp | grep -E ':(80|443|5000|8000)\s'
}

# 方案1: Let's Encrypt + Nginx
setup_letsencrypt() {
    echo ""
    echo "================================================"
    echo "Let's Encrypt + Nginx 配置"
    echo "================================================"
    echo ""
    
    # 输入域名
    read -p "请输入域名 (默认: $DOMAIN): " input_domain
    if [ ! -z "$input_domain" ]; then
        DOMAIN=$input_domain
    fi
    
    # 输入邮箱
    read -p "请输入邮箱 (默认: $EMAIL): " input_email
    if [ ! -z "$input_email" ]; then
        EMAIL=$input_email
    fi
    
    echo ""
    print_info "配置信息:"
    echo "  域名: $DOMAIN"
    echo "  邮箱: $EMAIL"
    echo ""
    
    # 安装依赖
    install_nginx
    install_certbot
    
    # 配置Nginx
    configure_nginx $DOMAIN
    
    # 配置防火墙
    configure_firewall
    
    # 获取证书
    get_letsencrypt_cert $DOMAIN $EMAIL
    
    echo ""
    echo "================================================"
    print_success "Let's Encrypt 配置完成"
    echo "================================================"
    echo ""
    echo "访问地址:"
    echo "  - Web界面: https://$DOMAIN"
    echo "  - API接口: https://$DOMAIN/api"
    echo "  - API文档: https://$DOMAIN/api/docs"
    echo ""
    echo "证书自动续期:"
    echo "  - 定期运行: certbot renew --dry-run"
    echo "  - 查看状态: systemctl status certbot.timer"
    echo ""
}

# 方案2: 自签名证书 + Flask
setup_self_signed() {
    echo ""
    echo "================================================"
    echo "自签名证书 + Flask 配置"
    echo "================================================"
    echo ""
    
    # 输入项目目录
    read -p "请输入项目目录 (默认: $PROJECT_DIR): " input_dir
    if [ ! -z "$input_dir" ]; then
        PROJECT_DIR=$input_dir
    fi
    
    echo ""
    print_info "配置信息:"
    echo "  项目目录: $PROJECT_DIR"
    echo ""
    
    # 生成证书
    generate_self_signed_cert $PROJECT_DIR
    
    # 更新配置
    update_app_config $PROJECT_DIR
    
    echo ""
    echo "================================================"
    print_success "自签名证书配置完成"
    echo "================================================"
    echo ""
    echo "下一步:"
    echo "  1. 编辑配置文件，添加SSL配置（参考上面提示）"
    echo "  2. 重启应用: python main.py restart"
    echo "  3. 访问: https://localhost:8000 (Web)"
    echo "         https://localhost:5000 (API)"
    echo ""
    echo "注意: 浏览器会显示安全警告，需要手动信任证书"
    echo ""
}

# 方案3: 仅生成证书
generate_cert_only() {
    echo ""
    echo "================================================"
    echo "生成自签名证书"
    echo "================================================"
    echo ""
    
    # 输入项目目录
    read -p "请输入项目目录 (默认: $PROJECT_DIR): " input_dir
    if [ ! -z "$input_dir" ]; then
        PROJECT_DIR=$input_dir
    fi
    
    generate_self_signed_cert $PROJECT_DIR
    
    echo ""
    print_success "证书生成完成"
    echo ""
}

# 主函数
main() {
    check_root
    
    while true; do
        show_menu
        read -p "请选择选项 (0-4): " choice
        
        case $choice in
            1)
                setup_letsencrypt
                ;;
            2)
                setup_self_signed
                ;;
            3)
                generate_cert_only
                ;;
            4)
                check_ssl_status
                ;;
            0)
                print_info "退出"
                exit 0
                ;;
            *)
                print_error "无效的选项，请重新选择"
                ;;
        esac
        
        echo ""
        read -p "按回车键继续..."
    done
}

# 运行主函数
main
