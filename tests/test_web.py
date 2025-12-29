"""
Web应用简单测试
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
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
        logger.info("Web应用测试")
        logger.info("=" * 60)
        
        # 创建Flask应用
        logger.info("创建Flask Web应用...")
        app = create_web_app(config)
        logger.info("✓ Flask Web应用创建成功")
        
        # 测试应用上下文
        logger.info("\n测试应用路由...")
        with app.app_context():
            with app.test_client() as client:
                # 测试仪表板
                logger.info("  测试 GET /")
                response = client.get('/')
                logger.info(f"    状态码: {response.status_code}")
                if response.status_code == 200:
                    logger.info(f"    ✓ 仪表板页面加载成功")
                else:
                    logger.error(f"    ✗ 请求失败")
                
                # 测试策略页面
                logger.info("\n  测试 GET /strategies/")
                response = client.get('/strategies/')
                logger.info(f"    状态码: {response.status_code}")
                if response.status_code == 200:
                    logger.info(f"    ✓ 策略页面加载成功")
                else:
                    logger.error(f"    ✗ 请求失败")
                
                # 测试策略表单页面
                logger.info("\n  测试 GET /strategies/create")
                response = client.get('/strategies/create')
                logger.info(f"    状态码: {response.status_code}")
                if response.status_code == 200:
                    logger.info(f"    ✓ 策略创建页面加载成功")
                else:
                    logger.error(f"    ✗ 请求失败")
                
                # 测试股票页面
                logger.info("\n  测试 GET /stocks/")
                response = client.get('/stocks/')
                logger.info(f"    状态码: {response.status_code}")
                if response.status_code == 200:
                    logger.info(f"    ✓ 股票页面加载成功")
                else:
                    logger.error(f"    ✗ 请求失败")
                
                # 测试数据管理页面
                logger.info("\n  测试 GET /data/")
                response = client.get('/data/')
                logger.info(f"    状态码: {response.status_code}")
                if response.status_code == 200:
                    logger.info(f"    ✓ 数据管理页面加载成功")
                else:
                    logger.error(f"    ✗ 请求失败")
                
                # 测试系统设置页面
                logger.info("\n  测试 GET /system/")
                response = client.get('/system/')
                logger.info(f"    状态码: {response.status_code}")
                if response.status_code == 200:
                    logger.info(f"    ✓ 系统设置页面加载成功")
                else:
                    logger.error(f"    ✗ 请求失败")
                
                # 测试系统日志页面
                logger.info("\n  测试 GET /system/logs")
                response = client.get('/system/logs')
                logger.info(f"    状态码: {response.status_code}")
                if response.status_code == 200:
                    logger.info(f"    ✓ 系统日志页面加载成功")
                else:
                    logger.error(f"    ✗ 请求失败")
                
                # 测试任务历史页面
                logger.info("\n  测试 GET /system/tasks")
                response = client.get('/system/tasks')
                logger.info(f"    状态码: {response.status_code}")
                if response.status_code == 200:
                    logger.info(f"    ✓ 任务历史页面加载成功")
                else:
                    logger.error(f"    ✗ 请求失败")
                
                # 测试404页面
                logger.info("\n  测试 GET /nonexistent")
                response = client.get('/nonexistent')
                logger.info(f"    状态码: {response.status_code}")
                if response.status_code == 404:
                    logger.info(f"    ✓ 404错误页面正常")
                else:
                    logger.error(f"    ✗ 404处理异常")
        
        logger.info("\n" + "=" * 60)
        logger.info("✓ Web应用测试完成！")
        logger.info("=" * 60)
        logger.info("\n提示：")
        logger.info("1. 运行 'python3 run_api.py' 启动API服务器（端口5000）")
        logger.info("2. 运行 'python3 run_web.py' 启动Web服务器（端口8000）")
        logger.info("3. 访问 http://localhost:8000 查看Web界面")
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
