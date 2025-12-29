#!/bin/bash
# Gunicorn 生产环境部署脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 项目路径
PROJECT_DIR="/data/home/aaronpan/stock-analysis-app"
SERVICE_DIR="/etc/systemd/system"

echo "=========================================="
echo "Gunicorn 生产环境部署脚本"
echo "=========================================="
echo

# 检查是否以 root 权限运行
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}请使用 sudo 运行此脚本${NC}"
    echo "命令: sudo ./deploy_gunicorn.sh"
    exit 1
fi

# 1. 安装 Gunicorn
echo -e "${YELLOW}[1/5] 安装 Gunicorn...${NC}"
cd "$PROJECT_DIR"
source venv/bin/activate
pip install gunicorn==21.2.0
echo -e "${GREEN}✓ Gunicorn 安装完成${NC}"
echo

# 2. 创建日志目录
echo -e "${YELLOW}[2/5] 创建日志目录...${NC}"
mkdir -p "$PROJECT_DIR/logs"
chmod 755 "$PROJECT_DIR/logs"
echo -e "${GREEN}✓ 日志目录已创建${NC}"
echo

# 3. 部署 systemd 服务文件
echo -e "${YELLOW}[3/5] 部署 systemd 服务文件...${NC}"
cp "$PROJECT_DIR/stock-api.service" "$SERVICE_DIR/"
cp "$PROJECT_DIR/stock-web.service" "$SERVICE_DIR/"
systemctl daemon-reload
echo -e "${GREEN}✓ 服务文件已部署${NC}"
echo

# 4. 启用服务
echo -e "${YELLOW}[4/5] 启用服务...${NC}"
systemctl enable stock-api.service
systemctl enable stock-web.service
echo -e "${GREEN}✓ 服务已启用${NC}"
echo

# 5. 启动服务
echo -e "${YELLOW}[5/5] 启动服务...${NC}"
systemctl start stock-api.service
systemctl start stock-web.service
echo -e "${GREEN}✓ 服务已启动${NC}"
echo

# 检查服务状态
echo "=========================================="
echo "服务状态"
echo "=========================================="
echo
echo "API 服务状态:"
systemctl status stock-api.service --no-pager -l
echo
echo "Web 服务状态:"
systemctl status stock-web.service --no-pager -l
echo

echo "=========================================="
echo "部署完成！"
echo "=========================================="
echo
echo "常用命令："
echo "  查看 API 服务状态: sudo systemctl status stock-api"
echo "  查看 Web 服务状态: sudo systemctl status stock-web"
echo "  启动 API 服务:     sudo systemctl start stock-api"
echo "  启动 Web 服务:     sudo systemctl start stock-web"
echo "  停止 API 服务:     sudo systemctl stop stock-api"
echo "  停止 Web 服务:     sudo systemctl stop stock-web"
echo "  重启 API 服务:     sudo systemctl restart stock-api"
echo "  重启 Web 服务:     sudo systemctl restart stock-web"
echo "  查看 API 日志:     sudo journalctl -u stock-api -f"
echo "  查看 Web 日志:     sudo journalctl -u stock-web -f"
echo
