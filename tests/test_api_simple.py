"""
简单的API启动测试
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.utils import get_config, setup_logging, get_logger
from app.api import create_app


def main():
    """主函数"""
    try:
        # 加载配置
        config = get_config()
        
        # 初始化日志系统
        setup_logging(config)
        logger = get_logger(__name__)
        
        logger.info("=" * 60)
        logger.info("API启动测试")
        logger.info("=" * 60)
        
        # 创建Flask应用
        logger.info("创建Flask应用...")
        app = create_app(config)
        logger.info("✓ Flask应用创建成功")
        
        # 测试应用上下文
        logger.info("\n测试应用上下文...")
        with app.app_context():
            # 测试根路径
            with app.test_client() as client:
                logger.info("  测试 GET /")
                response = client.get('/')
                logger.info(f"    状态码: {response.status_code}")
                if response.status_code == 200:
                    data = response.get_json()
                    logger.info(f"    ✓ 系统名称: {data['name']}")
                    logger.info(f"    ✓ 版本: {data['version']}")
                else:
                    logger.error(f"    ✗ 请求失败")
                
                # 测试健康检查
                logger.info("\n  测试 GET /health")
                response = client.get('/health')
                logger.info(f"    状态码: {response.status_code}")
                if response.status_code == 200:
                    data = response.get_json()
                    logger.info(f"    ✓ 状态: {data['status']}")
                    logger.info(f"    ✓ SQLite: {data['database']['sqlite']}")
                    logger.info(f"    ✓ DuckDB: {data['database']['duckdb']}")
                else:
                    logger.error(f"    ✗ 请求失败")
                
                # 测试系统信息
                logger.info("\n  测试 GET /api/system/info")
                response = client.get('/api/system/info')
                logger.info(f"    状态码: {response.status_code}")
                if response.status_code == 200:
                    data = response.get_json()
                    if data['success']:
                        logger.info(f"    ✓ 系统名称: {data['data']['name']}")
                        logger.info(f"    ✓ 数据源: {data['data']['datasource']}")
                    else:
                        logger.error(f"    ✗ 请求失败: {data.get('error')}")
                else:
                    logger.error(f"    ✗ 请求失败")
                
                # 测试系统统计
                logger.info("\n  测试 GET /api/system/stats")
                response = client.get('/api/system/stats')
                logger.info(f"    状态码: {response.status_code}")
                if response.status_code == 200:
                    data = response.get_json()
                    if data['success']:
                        stats = data['data']
                        logger.info(f"    ✓ 股票总数: {stats['stocks']['total']}")
                        logger.info(f"    ✓ 策略总数: {stats['strategies']['total']}")
                        logger.info(f"    ✓ 行情记录: {stats['market_data']['record_count']}")
                    else:
                        logger.error(f"    ✗ 请求失败: {data.get('error')}")
                else:
                    logger.error(f"    ✗ 请求失败")
                
                # 测试股票列表
                logger.info("\n  测试 GET /api/stocks?limit=5")
                response = client.get('/api/stocks?limit=5')
                logger.info(f"    状态码: {response.status_code}")
                if response.status_code == 200:
                    data = response.get_json()
                    if data['success']:
                        logger.info(f"    ✓ 返回数量: {len(data['data'])}")
                        logger.info(f"    ✓ 总数: {data['pagination']['total']}")
                        if data['data']:
                            stock = data['data'][0]
                            logger.info(f"    ✓ 示例: {stock['code']} - {stock['name']}")
                    else:
                        logger.error(f"    ✗ 请求失败: {data.get('error')}")
                else:
                    logger.error(f"    ✗ 请求失败")
                
                # 测试策略列表
                logger.info("\n  测试 GET /api/strategies")
                response = client.get('/api/strategies')
                logger.info(f"    状态码: {response.status_code}")
                if response.status_code == 200:
                    data = response.get_json()
                    if data['success']:
                        logger.info(f"    ✓ 策略数量: {data['count']}")
                    else:
                        logger.error(f"    ✗ 请求失败: {data.get('error')}")
                else:
                    logger.error(f"    ✗ 请求失败")
        
        logger.info("\n" + "=" * 60)
        logger.info("✓ API启动测试完成！")
        logger.info("=" * 60)
        logger.info("\n提示：运行 'python3 run_api.py' 启动API服务器")
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
