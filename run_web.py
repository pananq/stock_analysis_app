"""
Flask Web应用启动脚本
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.utils import get_config, setup_logging, get_logger
from app.web import create_web_app


def main():
    """主函数"""
    try:
        # 加载配置
        config = get_config()
        
        # 初始化日志系统
        setup_logging(config)
        logger = get_logger(__name__)
        
        logger.info("=" * 60)
        logger.info("股海罗盘 - Web服务器")
        logger.info("=" * 60)
        
        # 创建Flask应用
        app = create_web_app(config)
        
        # 获取Web配置
        web_config = config.get('web', {})
        host = web_config.get('host', '0.0.0.0')
        port = web_config.get('port', 8000)
        debug = web_config.get('debug', False)
        
        logger.info(f"Web服务器启动: http://{host}:{port}")
        logger.info("=" * 60)
        
        # 启动Flask应用
        app.run(
            host=host,
            port=port,
            debug=debug
        )
        
    except KeyboardInterrupt:
        logger.info("\n收到中断信号，正在关闭...")
        logger.info("Web服务器已关闭")
        
    except Exception as e:
        print(f"启动失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
