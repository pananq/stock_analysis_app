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
from app.scheduler import get_task_scheduler


def main():
    """主函数"""
    try:
        # 加载配置
        config = get_config()
        
        # 初始化日志系统
        setup_logging(config)
        logger = get_logger(__name__)
        
        logger.info("=" * 60)
        logger.info("股票分析系统 - Web服务器")
        logger.info("=" * 60)
        
        # 初始化并启动任务调度器
        try:
            scheduler_config = config.get('scheduler', {})
            if scheduler_config.get('enable_auto_update', True):
                logger.info("初始化任务调度器...")
                scheduler = get_task_scheduler()
                
                # 添加定时任务
                stock_update_time = scheduler_config.get('stock_list_update_time', '18:00')
                hour, minute = map(int, stock_update_time.split(':'))
                scheduler.add_daily_stock_update_job(hour=hour, minute=minute)
                logger.info(f"  ✓ 每日股票更新任务 ({stock_update_time})")
                
                market_update_time = scheduler_config.get('market_data_update_time', '18:30')
                hour, minute = map(int, market_update_time.split(':'))
                scheduler.add_daily_market_data_update_job(hour=hour, minute=minute)
                logger.info(f"  ✓ 每日行情数据更新任务 ({market_update_time})")
                
                # 策略执行任务在行情更新后30分钟
                hour, minute = map(int, market_update_time.split(':'))
                minute += 30
                if minute >= 60:
                    hour += 1
                    minute -= 60
                scheduler.add_daily_strategy_execution_job(hour=hour, minute=minute)
                logger.info(f"  ✓ 每日策略执行任务 ({hour:02d}:{minute:02d})")
                
                # 启动调度器
                scheduler.start()
                logger.info("✓ 任务调度器已启动")
            else:
                logger.info("任务调度器已禁用（配置：scheduler.enable_auto_update=false）")
        except Exception as e:
            logger.error(f"启动任务调度器失败: {e}")
            logger.warning("Web服务器将继续运行，但定时任务不可用")
        
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
