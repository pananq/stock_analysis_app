"""
快速测试增量更新功能（只更新少量股票）
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.utils import get_config, setup_logging, get_logger
from app.models import get_sqlite_db, get_duckdb
from app.services import get_market_data_service


def test_quick_update():
    """快速测试增量更新（只更新前3只股票）"""
    logger = get_logger(__name__)
    
    logger.info("=" * 60)
    logger.info("快速测试增量更新功能（前3只股票）")
    logger.info("=" * 60)
    
    # 获取行情数据服务
    market_service = get_market_data_service()
    
    # 1. 查看当前数据统计
    logger.info("\n步骤1: 查看更新前的数据统计")
    stats_before = market_service.get_statistics()
    logger.info(f"  总记录数: {stats_before['total_records']}")
    logger.info(f"  股票数量: {stats_before['stock_count']}")
    logger.info(f"  最晚日期: {stats_before['latest_date']}")
    
    # 2. 获取已有数据的股票列表（只取前3只）
    query = "SELECT DISTINCT code FROM daily_market LIMIT 3"
    result = market_service.duckdb.execute_query(query)
    test_codes = [row['code'] for row in result]
    
    logger.info(f"\n步骤2: 准备更新的测试股票: {', '.join(test_codes)}")
    
    # 查看这些股票更新前的最新数据
    for code in test_codes:
        latest = market_service.get_latest_data(code)
        if latest:
            logger.info(f"  {code}: 最新日期={latest['trade_date']}, 收盘价={latest['close']}")
    
    # 3. 执行增量更新
    logger.info("\n步骤3: 执行增量更新（最近5天）")
    
    start_time = datetime.now()
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')
    
    success_count = 0
    fail_count = 0
    total_records = 0
    
    for code in test_codes:
        try:
            logger.info(f"  正在更新 {code}...")
            
            # API频率控制
            market_service.rate_limiter.wait()
            
            # 获取最近的行情数据
            df = market_service.datasource.get_daily_data(code, start_date, end_date)
            
            if df.empty:
                logger.warning(f"    {code} 未获取到数据")
                fail_count += 1
                continue
            
            # 删除该股票在日期范围内的旧数据
            market_service._delete_data_in_range(code, start_date, end_date)
            
            # 保存新数据
            records = len(df)
            market_service._save_daily_data(df, code)
            
            success_count += 1
            total_records += records
            logger.info(f"    ✓ {code} 更新成功，{records}条记录")
            
        except Exception as e:
            logger.error(f"    ✗ {code} 更新失败: {e}")
            fail_count += 1
    
    duration = (datetime.now() - start_time).total_seconds()
    
    # 4. 显示更新结果
    logger.info("\n步骤4: 更新结果")
    logger.info(f"  成功: {success_count}/{len(test_codes)}")
    logger.info(f"  失败: {fail_count}/{len(test_codes)}")
    logger.info(f"  总记录数: {total_records}")
    logger.info(f"  耗时: {duration:.2f}秒")
    
    # 5. 查看更新后的数据统计
    logger.info("\n步骤5: 查看更新后的数据统计")
    stats_after = market_service.get_statistics()
    logger.info(f"  总记录数: {stats_after['total_records']}")
    logger.info(f"  股票数量: {stats_after['stock_count']}")
    logger.info(f"  最晚日期: {stats_after['latest_date']}")
    
    # 6. 查看测试股票更新后的最新数据
    logger.info("\n步骤6: 查看测试股票更新后的最新数据")
    for code in test_codes:
        latest = market_service.get_latest_data(code)
        if latest:
            logger.info(f"  {code}: 最新日期={latest['trade_date']}, 收盘价={latest['close']}")
        
        # 显示最近5条数据
        logger.info(f"\n  {code} 最近5条数据:")
        df = market_service.get_stock_data(code, limit=5)
        if not df.empty:
            for _, row in df.iterrows():
                logger.info(f"    {row['trade_date']}: 开={row['open']}, 收={row['close']}, 高={row['high']}, 低={row['low']}")
    
    logger.info("\n" + "=" * 60)
    logger.info("✓ 增量更新测试完成！")
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
        logger.info("股票分析系统 - 快速增量更新测试")
        logger.info("=" * 60)
        
        # 初始化数据库
        sqlite_db = get_sqlite_db()
        duckdb = get_duckdb()
        logger.info("数据库初始化完成")
        
        # 测试增量更新功能
        test_quick_update()
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
