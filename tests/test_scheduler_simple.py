"""
简化的任务调度器测试
"""
import sys
import time
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.utils import get_config, setup_logging, get_logger
from app.models import get_sqlite_db, get_duckdb
from app.scheduler import get_task_scheduler
from app.services import get_strategy_service


def main():
    """主函数"""
    try:
        # 加载配置
        config = get_config()
        
        # 初始化日志系统
        setup_logging(config)
        logger = get_logger(__name__)
        
        logger.info("=" * 60)
        logger.info("任务调度器简化测试")
        logger.info("=" * 60)
        
        # 初始化数据库
        sqlite_db = get_sqlite_db()
        duckdb = get_duckdb()
        logger.info("✓ 数据库初始化完成")
        
        # 获取任务调度器
        scheduler = get_task_scheduler()
        logger.info("✓ 任务调度器初始化完成")
        
        # 添加定时任务
        logger.info("\n添加定时任务:")
        scheduler.add_daily_stock_update_job(hour=18, minute=0)
        logger.info("  ✓ 每日股票更新任务 (18:00)")
        
        scheduler.add_daily_market_data_update_job(hour=18, minute=30)
        logger.info("  ✓ 每日行情数据更新任务 (18:30)")
        
        scheduler.add_daily_strategy_execution_job(hour=19, minute=0)
        logger.info("  ✓ 每日策略执行任务 (19:00)")
        
        scheduler.add_periodic_health_check_job(interval_minutes=30)
        logger.info("  ✓ 定期健康检查任务 (每30分钟)")
        
        # 启动调度器
        logger.info("\n启动调度器...")
        scheduler.start()
        logger.info("✓ 调度器已启动")
        
        # 查看任务列表
        jobs = scheduler.get_jobs()
        logger.info(f"\n当前任务列表 ({len(jobs)}个):")
        for job in jobs:
            logger.info(f"  - {job['name']} (ID: {job['id']})")
        
        # 测试健康检查
        logger.info("\n测试健康检查...")
        scheduler.run_job_now('periodic_health_check')
        time.sleep(2)
        logger.info("✓ 健康检查完成")
        
        # 检查是否有行情数据和策略
        result = duckdb.execute_query(
            "SELECT COUNT(DISTINCT code) as stock_count FROM daily_market"
        )
        stock_count = result[0]['stock_count'] if result else 0
        
        strategy_service = get_strategy_service()
        strategies = strategy_service.list_strategies(enabled_only=True)
        
        logger.info(f"\n系统状态:")
        logger.info(f"  - 行情数据: {stock_count} 只股票")
        logger.info(f"  - 启用策略: {len(strategies)} 个")
        
        if stock_count > 0 and len(strategies) > 0:
            logger.info("\n测试策略执行...")
            scheduler.run_job_now('daily_strategy_execution')
            logger.info("  策略执行任务已触发，等待完成...")
            time.sleep(15)
            
            # 查看执行日志
            logs = scheduler.get_job_logs(limit=1)
            if logs:
                log = logs[0]
                logger.info(f"\n最新任务执行结果:")
                logger.info(f"  任务: {log['job_name']}")
                logger.info(f"  状态: {log['status']}")
                if log.get('duration'):
                    logger.info(f"  时长: {log['duration']:.2f}秒")
                if log.get('message'):
                    logger.info(f"  消息: {log['message']}")
        else:
            logger.info("\n⚠ 跳过策略执行测试（需要行情数据和启用的策略）")
        
        # 查看任务日志统计
        log_count = scheduler.get_job_logs_count()
        logger.info(f"\n任务日志总数: {log_count}")
        
        # 关闭调度器
        logger.info("\n关闭调度器...")
        scheduler.shutdown(wait=True)
        logger.info("✓ 调度器已关闭")
        
        logger.info("\n" + "=" * 60)
        logger.info("✓ 测试完成！")
        logger.info("=" * 60)
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
