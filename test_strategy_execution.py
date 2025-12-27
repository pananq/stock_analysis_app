"""
测试策略执行引擎
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.utils import get_config, setup_logging, get_logger
from app.models import get_sqlite_db, get_duckdb
from app.services import get_strategy_service, get_strategy_executor


def test_strategy_execution():
    """测试策略执行引擎"""
    logger = get_logger(__name__)
    
    logger.info("=" * 60)
    logger.info("测试策略执行引擎")
    logger.info("=" * 60)
    
    # 获取服务
    strategy_service = get_strategy_service()
    executor = get_strategy_executor()
    
    # 1. 创建测试策略
    logger.info("\n步骤1: 创建测试策略")
    
    strategy_id = strategy_service.create_strategy(
        name="测试策略-大涨后站稳5日线",
        description="单日涨幅超过8%，随后3天收盘价均高于5日均线",
        rise_threshold=8.0,
        observation_days=3,
        ma_period=5,
        enabled=True
    )
    
    if strategy_id:
        logger.info(f"  ✓ 测试策略创建成功，ID: {strategy_id}")
    else:
        logger.error("  ✗ 测试策略创建失败")
        return
    
    # 2. 检查数据库中是否有行情数据
    logger.info("\n步骤2: 检查行情数据")
    
    duckdb = get_duckdb()
    result = duckdb.execute_query(
        "SELECT COUNT(DISTINCT code) as stock_count, COUNT(*) as record_count FROM daily_market"
    )
    
    if result:
        stock_count = result[0]['stock_count']
        record_count = result[0]['record_count']
        logger.info(f"  数据库中有 {stock_count} 只股票，共 {record_count} 条行情记录")
        
        if stock_count == 0:
            logger.warning("  ⚠ 数据库中没有行情数据，请先运行数据导入")
            logger.info("  提示: 可以运行 test_market_data.py 导入测试数据")
            return
    else:
        logger.error("  ✗ 无法查询行情数据")
        return
    
    # 3. 执行策略（限制扫描10只股票进行测试）
    logger.info("\n步骤3: 执行策略（测试模式，限制10只股票）")
    
    result = executor.execute_strategy(
        strategy_id=strategy_id,
        start_date="2024-01-01",
        end_date="2024-12-31",
        limit_stocks=10
    )
    
    if result['success']:
        logger.info(f"  ✓ 策略执行成功")
        logger.info(f"    策略名称: {result['strategy_name']}")
        logger.info(f"    扫描股票数: {result['scanned_stocks']}")
        logger.info(f"    匹配数量: {result['matched_count']}")
        logger.info(f"    保存记录数: {result['saved_count']}")
        
        if result['matched_count'] > 0:
            logger.info(f"\n  前几个匹配结果:")
            for i, match in enumerate(result['matches'][:5], 1):
                logger.info(f"\n    匹配 {i}:")
                logger.info(f"      股票: {match['stock_code']} {match['stock_name']}")
                logger.info(f"      触发日期: {match['trigger_date']}")
                logger.info(f"      触发涨幅: {match['trigger_pct_change']:.2f}%")
                logger.info(f"      观察天数: {match['observation_days']}")
                logger.info(f"      均线周期: {match['ma_period']}日")
                
                obs_result = match['observation_result']
                logger.info(f"      观察结果: {obs_result['days_above_ma']}/{obs_result['days_checked']} 天站在均线之上")
                
                if obs_result['details']:
                    logger.info(f"      详细数据:")
                    for detail in obs_result['details']:
                        status = "✓" if detail['above_ma'] else "✗"
                        ma_key = f"ma{match['ma_period']}"
                        logger.info(f"        {status} {detail['date']}: 收盘={detail['close']:.2f}, MA{match['ma_period']}={detail[ma_key]:.2f}")
        else:
            logger.info("  ℹ 未找到符合条件的股票")
    else:
        logger.error(f"  ✗ 策略执行失败: {result.get('error', '未知错误')}")
        return
    
    # 4. 查询策略执行结果
    logger.info("\n步骤4: 查询策略执行结果")
    
    results_count = executor.get_strategy_results_count(strategy_id)
    logger.info(f"  策略结果总数: {results_count}")
    
    if results_count > 0:
        results = executor.get_strategy_results(strategy_id, limit=5)
        logger.info(f"  获取前5条结果:")
        
        for i, result in enumerate(results, 1):
            logger.info(f"\n    结果 {i}:")
            logger.info(f"      股票: {result['stock_code']} {result['stock_name']}")
            logger.info(f"      触发日期: {result['trigger_date']}")
            logger.info(f"      触发涨幅: {result['trigger_pct_change']:.2f}%")
            logger.info(f"      创建时间: {result['created_at']}")
    
    # 5. 测试更大范围的扫描（如果数据足够）
    if stock_count >= 50:
        logger.info("\n步骤5: 测试更大范围扫描（50只股票）")
        
        # 清空之前的结果
        executor.clear_strategy_results(strategy_id)
        logger.info("  已清空之前的结果")
        
        result = executor.execute_strategy(
            strategy_id=strategy_id,
            start_date="2024-01-01",
            end_date="2024-12-31",
            limit_stocks=50
        )
        
        if result['success']:
            logger.info(f"  ✓ 策略执行成功")
            logger.info(f"    扫描股票数: {result['scanned_stocks']}")
            logger.info(f"    匹配数量: {result['matched_count']}")
            logger.info(f"    保存记录数: {result['saved_count']}")
        else:
            logger.error(f"  ✗ 策略执行失败: {result.get('error', '未知错误')}")
    
    # 6. 测试不同的策略参数
    logger.info("\n步骤6: 测试不同的策略参数")
    
    strategy_id2 = strategy_service.create_strategy(
        name="测试策略-温和上涨",
        description="单日涨幅超过5%，随后5天收盘价均高于10日均线",
        rise_threshold=5.0,
        observation_days=5,
        ma_period=10,
        enabled=True
    )
    
    if strategy_id2:
        logger.info(f"  ✓ 第二个测试策略创建成功，ID: {strategy_id2}")
        
        result = executor.execute_strategy(
            strategy_id=strategy_id2,
            start_date="2024-01-01",
            end_date="2024-12-31",
            limit_stocks=10
        )
        
        if result['success']:
            logger.info(f"  ✓ 第二个策略执行成功")
            logger.info(f"    扫描股票数: {result['scanned_stocks']}")
            logger.info(f"    匹配数量: {result['matched_count']}")
        else:
            logger.error(f"  ✗ 第二个策略执行失败: {result.get('error', '未知错误')}")
    
    # 7. 测试禁用的策略
    logger.info("\n步骤7: 测试禁用的策略")
    
    strategy_service.update_strategy(strategy_id, enabled=False)
    logger.info(f"  已禁用策略 {strategy_id}")
    
    result = executor.execute_strategy(strategy_id=strategy_id, limit_stocks=5)
    
    if not result['success'] and '未启用' in result.get('error', ''):
        logger.info("  ✓ 正确拒绝了禁用的策略")
    else:
        logger.error("  ✗ 未能正确处理禁用的策略")
    
    # 8. 检查策略的最后执行时间
    logger.info("\n步骤8: 检查策略的最后执行时间")
    
    strategy = strategy_service.get_strategy(strategy_id2)
    if strategy and strategy['last_executed_at']:
        logger.info(f"  ✓ 策略最后执行时间已更新: {strategy['last_executed_at']}")
    else:
        logger.warning("  ⚠ 策略最后执行时间未更新")
    
    logger.info("\n" + "=" * 60)
    logger.info("✓ 策略执行引擎测试完成！")
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
        logger.info("股票分析系统 - 策略执行引擎测试")
        logger.info("=" * 60)
        
        # 初始化数据库
        sqlite_db = get_sqlite_db()
        duckdb = get_duckdb()
        logger.info("数据库初始化完成")
        
        # 测试策略执行引擎
        test_strategy_execution()
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
