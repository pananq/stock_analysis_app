"""
测试任务调度器
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


def test_task_scheduler():
    """测试任务调度器"""
    logger = get_logger(__name__)
    
    logger.info("=" * 60)
    logger.info("测试任务调度器")
    logger.info("=" * 60)
    
    # 获取任务调度器
    scheduler = get_task_scheduler()
    
    # 1. 测试添加定时任务
    logger.info("\n步骤1: 添加定时任务")
    
    # 添加每日股票更新任务（每天18:00）
    scheduler.add_daily_stock_update_job(hour=18, minute=0)
    logger.info("  ✓ 已添加每日股票更新任务")
    
    # 添加每日行情数据更新任务（每天18:30）
    scheduler.add_daily_market_data_update_job(hour=18, minute=30)
    logger.info("  ✓ 已添加每日行情数据更新任务")
    
    # 添加每日策略执行任务（每天19:00）
    scheduler.add_daily_strategy_execution_job(hour=19, minute=0)
    logger.info("  ✓ 已添加每日策略执行任务")
    
    # 添加定期健康检查任务（每30分钟）
    scheduler.add_periodic_health_check_job(interval_minutes=30)
    logger.info("  ✓ 已添加定期健康检查任务")
    
    # 2. 查看所有任务
    logger.info("\n步骤2: 查看所有任务")
    
    jobs = scheduler.get_jobs()
    logger.info(f"  当前共有 {len(jobs)} 个任务:")
    
    for job in jobs:
        logger.info(f"\n    任务ID: {job['id']}")
        logger.info(f"    任务名称: {job['name']}")
        logger.info(f"    下次执行: {job['next_run_time']}")
        logger.info(f"    触发器: {job['trigger']}")
    
    # 3. 启动调度器
    logger.info("\n步骤3: 启动调度器")
    
    scheduler.start()
    logger.info("  ✓ 调度器已启动")
    
    # 4. 测试立即执行任务
    logger.info("\n步骤4: 测试立即执行任务")
    
    # 测试健康检查
    logger.info("  触发健康检查任务...")
    success = scheduler.run_job_now('periodic_health_check')
    
    if success:
        logger.info("  ✓ 健康检查任务已触发")
        time.sleep(2)  # 等待任务执行
    else:
        logger.error("  ✗ 健康检查任务触发失败")
    
    # 5. 测试手动执行股票更新（如果有数据源配置）
    logger.info("\n步骤5: 测试手动执行股票更新")
    
    config = get_config()
    datasource_type = config.get('datasource', {}).get('type', 'akshare')
    
    if datasource_type == 'akshare':
        logger.info("  使用AKShare数据源，可以测试股票更新")
        logger.info("  触发股票列表更新任务...")
        
        success = scheduler.run_job_now('daily_stock_update')
        
        if success:
            logger.info("  ✓ 股票列表更新任务已触发")
            logger.info("  等待任务执行（可能需要较长时间）...")
            time.sleep(10)  # 等待任务执行
        else:
            logger.error("  ✗ 股票列表更新任务触发失败")
    else:
        logger.info(f"  当前数据源: {datasource_type}")
        logger.info("  跳过股票更新测试（需要配置数据源）")
    
    # 6. 查看任务执行日志
    logger.info("\n步骤6: 查看任务执行日志")
    
    logs = scheduler.get_job_logs(limit=10)
    log_count = scheduler.get_job_logs_count()
    
    logger.info(f"  任务日志总数: {log_count}")
    
    if logs:
        logger.info(f"  最近 {len(logs)} 条日志:")
        
        for log in logs:
            logger.info(f"\n    日志ID: {log['id']}")
            logger.info(f"    任务类型: {log['job_type']}")
            logger.info(f"    任务名称: {log['job_name']}")
            logger.info(f"    状态: {log['status']}")
            logger.info(f"    开始时间: {log['started_at']}")
            
            if log['completed_at']:
                logger.info(f"    完成时间: {log['completed_at']}")
                logger.info(f"    执行时长: {log['duration']:.2f}秒")
            
            if log['message']:
                logger.info(f"    消息: {log['message']}")
            
            if log['error']:
                logger.info(f"    错误: {log['error']}")
    else:
        logger.info("  暂无任务执行日志")
    
    # 7. 测试移除任务
    logger.info("\n步骤7: 测试移除任务")
    
    # 移除健康检查任务
    success = scheduler.remove_job('periodic_health_check')
    
    if success:
        logger.info("  ✓ 健康检查任务已移除")
    else:
        logger.error("  ✗ 健康检查任务移除失败")
    
    # 再次查看任务列表
    jobs = scheduler.get_jobs()
    logger.info(f"  当前共有 {len(jobs)} 个任务")
    
    # 8. 测试清理旧日志
    logger.info("\n步骤8: 测试清理旧日志")
    
    deleted_count = scheduler.clear_old_job_logs(days=30)
    logger.info(f"  ✓ 清理了 {deleted_count} 条旧日志")
    
    # 9. 关闭调度器
    logger.info("\n步骤9: 关闭调度器")
    
    scheduler.shutdown(wait=True)
    logger.info("  ✓ 调度器已关闭")
    
    logger.info("\n" + "=" * 60)
    logger.info("✓ 任务调度器测试完成！")
    logger.info("=" * 60)


def test_scheduler_with_real_tasks():
    """测试调度器执行真实任务"""
    logger = get_logger(__name__)
    
    logger.info("\n" + "=" * 60)
    logger.info("测试调度器执行真实任务")
    logger.info("=" * 60)
    
    # 获取任务调度器
    scheduler = get_task_scheduler()
    
    # 检查是否有行情数据
    duckdb = get_duckdb()
    result = duckdb.execute_query(
        "SELECT COUNT(DISTINCT code) as stock_count FROM daily_market"
    )
    
    stock_count = result[0]['stock_count'] if result else 0
    
    if stock_count == 0:
        logger.warning("  ⚠ 数据库中没有行情数据，跳过策略执行测试")
        return
    
    logger.info(f"  数据库中有 {stock_count} 只股票的行情数据")
    
    # 检查是否有启用的策略
    from app.services import get_strategy_service
    strategy_service = get_strategy_service()
    
    strategies = strategy_service.list_strategies(enabled_only=True)
    
    if not strategies:
        logger.info("  创建测试策略...")
        
        strategy_id = strategy_service.create_strategy(
            name="调度器测试策略",
            description="用于测试调度器的策略",
            rise_threshold=5.0,
            observation_days=3,
            ma_period=5,
            enabled=True
        )
        
        if strategy_id:
            logger.info(f"  ✓ 测试策略创建成功，ID: {strategy_id}")
        else:
            logger.error("  ✗ 测试策略创建失败")
            return
    else:
        logger.info(f"  找到 {len(strategies)} 个启用的策略")
    
    # 启动调度器
    scheduler.start()
    logger.info("  ✓ 调度器已启动")
    
    # 添加策略执行任务
    scheduler.add_daily_strategy_execution_job(hour=19, minute=0)
    
    # 手动触发策略执行任务
    logger.info("\n  触发策略执行任务...")
    
    success = scheduler.run_job_now('daily_strategy_execution')
    
    if success:
        logger.info("  ✓ 策略执行任务已触发")
        logger.info("  等待任务执行...")
        time.sleep(15)  # 等待任务执行
        
        # 查看执行日志
        logs = scheduler.get_job_logs(limit=1)
        
        if logs:
            log = logs[0]
            logger.info(f"\n  最新任务执行结果:")
            logger.info(f"    任务: {log['job_name']}")
            logger.info(f"    状态: {log['status']}")
            logger.info(f"    执行时长: {log.get('duration', 0):.2f}秒")
            
            if log['message']:
                logger.info(f"    消息: {log['message']}")
            
            if log['error']:
                logger.info(f"    错误: {log['error']}")
    else:
        logger.error("  ✗ 策略执行任务触发失败")
    
    # 关闭调度器
    scheduler.shutdown(wait=True)
    logger.info("\n  ✓ 调度器已关闭")
    
    logger.info("\n" + "=" * 60)
    logger.info("✓ 真实任务测试完成！")
    logger.info("=" * 60)


def main():
    """主函数"""
    try:
        # 加载配置
        config = get_config()
        
        # 初始化日志系统
        setup_logging(config)
        logger = get_logger(__name__)
        
        logger.info("=" * 60)
        logger.info("股票分析系统 - 任务调度器测试")
        logger.info("=" * 60)
        
        # 初始化数据库
        sqlite_db = get_sqlite_db()
        duckdb = get_duckdb()
        logger.info("数据库初始化完成")
        
        # 测试任务调度器基本功能
        test_task_scheduler()
        
        # 测试调度器执行真实任务
        test_scheduler_with_real_tasks()
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
