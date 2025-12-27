#!/usr/bin/env python3
"""
股票分析系统 API 启动脚本
"""
import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from app.api.app import create_app
import argparse
from app.utils import get_logger

logger = get_logger(__name__)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='股票分析系统 API 服务')
    parser.add_argument('--host', default='0.0.0.0', help='主机地址')
    parser.add_argument('--port', type=int, default=5000, help='端口号')
    parser.add_argument('--debug', action='store_true', help='调试模式')
    
    args = parser.parse_args()
    
    app = create_app()
    logger.info(f"启动 API 服务: http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug)

if __name__ == '__main__':
    main()
