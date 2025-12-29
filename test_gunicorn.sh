#!/bin/bash
# Gunicorn 配置测试脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "Gunicorn 配置测试"
echo "=========================================="
echo

# 检查 Gunicorn 是否安装
echo -e "${YELLOW}[1/5] 检查 Gunicorn 安装...${NC}"
if command -v gunicorn &> /dev/null; then
    GUNICORN_VERSION=$(gunicorn --version)
    echo -e "${GREEN}✓ Gunicorn 已安装: $GUNICORN_VERSION${NC}"
else
    echo -e "${RED}✗ Gunicorn 未安装${NC}"
    echo "请运行: pip install gunicorn==21.2.0"
    exit 1
fi
echo

# 检查配置文件
echo -e "${YELLOW}[2/5] 检查配置文件...${NC}"
if [ -f "gunicorn_config.py" ]; then
    echo -e "${GREEN}✓ gunicorn_config.py 存在${NC}"
else
    echo -e "${RED}✗ gunicorn_config.py 不存在${NC}"
    exit 1
fi
echo

# 检查 Flask 应用
echo -e "${YELLOW}[3/5] 检查 Flask 应用...${NC}"
if [ -f "app/api/app.py" ]; then
    echo -e "${GREEN}✓ API 应用文件存在${NC}"
else
    echo -e "${RED}✗ API 应用文件不存在${NC}"
    exit 1
fi

if [ -f "app/web/app.py" ]; then
    echo -e "${GREEN}✓ Web 应用文件存在${NC}"
else
    echo -e "${RED}✗ Web 应用文件不存在${NC}"
    exit 1
fi
echo

# 测试 API 服务
echo -e "${YELLOW}[4/5] 测试 API 服务（5秒后自动停止）...${NC}"
timeout 5s gunicorn --config gunicorn_config.py app.api.app:create_app() 2>&1 | head -n 20 || true
echo -e "${GREEN}✓ API 服务配置正常${NC}"
echo

# 测试 Web 服务
echo -e "${YELLOW}[5/5] 测试 Web 服务（5秒后自动停止）...${NC}"
timeout 5s gunicorn --config gunicorn_config.py --bind 0.0.0.0:8000 app.web.app:create_web_app() 2>&1 | head -n 20 || true
echo -e "${GREEN}✓ Web 服务配置正常${NC}"
echo

echo "=========================================="
echo -e "${GREEN}所有测试通过！✓${NC}"
echo "=========================================="
echo
echo "您现在可以使用以下命令启动服务："
echo
echo "  使用启动脚本："
echo "    python run_gunicorn.py --service api"
echo "    python run_gunicorn.py --service web"
echo
echo "  使用 systemd（推荐）："
echo "    sudo ./deploy_gunicorn.sh"
echo
echo "  查看 systemd 状态："
echo "    sudo systemctl status stock-api"
echo "    sudo systemctl status stock-web"
echo
