#!/usr/bin/env python3
"""
Gunicorn 生产环境启动脚本
"""
import sys
import os
import subprocess
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def start_gunicorn_api():
    """使用 Gunicorn 启动 API 服务器"""
    print("=" * 60)
    print("启动 Gunicorn API 服务器（生产环境）")
    print("=" * 60)
    
    # Gunicorn 命令
    cmd = [
        "gunicorn",
        "--config", "gunicorn_config.py",
        "app.api.app:create_app()",
    ]
    
    print(f"执行命令: {' '.join(cmd)}")
    print()
    
    # 执行命令
    try:
        subprocess.run(cmd, cwd=project_root, check=True)
    except subprocess.CalledProcessError as e:
        print(f"启动失败: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n收到中断信号，正在停止服务器...")
        sys.exit(0)


def start_gunicorn_web():
    """使用 Gunicorn 启动 Web 服务器"""
    print("=" * 60)
    print("启动 Gunicorn Web 服务器（生产环境）")
    print("=" * 60)
    
    # Gunicorn 命令
    cmd = [
        "gunicorn",
        "--config", "gunicorn_config.py",
        "--bind", "0.0.0.0:8000",
        "app.web.app:create_web_app()",
    ]
    
    print(f"执行命令: {' '.join(cmd)}")
    print()
    
    # 执行命令
    try:
        subprocess.run(cmd, cwd=project_root, check=True)
    except subprocess.CalledProcessError as e:
        print(f"启动失败: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n收到中断信号，正在停止服务器...")
        sys.exit(0)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Gunicorn 生产环境启动脚本")
    parser.add_argument(
        "--service",
        choices=["api", "web", "all"],
        default="api",
        help="要启动的服务类型 (api/web/all)"
    )
    
    args = parser.parse_args()
    
    if args.service == "api":
        start_gunicorn_api()
    elif args.service == "web":
        start_gunicorn_web()
    elif args.service == "all":
        print("启动所有服务...")
        # 在生产环境中，通常使用 systemd 或 supervisor 分别管理 api 和 web 服务
        # 这里只是示例，实际建议分别启动
        print("请分别运行以下命令启动服务：")
        print("  python run_gunicorn.py --service api")
        print("  python run_gunicorn.py --service web")
