"""
测试历史行情数据增量更新功能
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.utils import get_config, setup_logging, get_logger
from app.models import get_sqlite_db, get_duckdb
from app.services import get_market_data_service


def test_incremental_update():
    """测试增量更新功能"""
    logger = get_logger(__name__)
    
    logger.info("=" * 60)
    logger.info("测试历史行情数据增量更新功能")
    logger.info("=" * 60)
    
    # 获取行情数据服务
    market_service = get_market_data_service()
    
    # 1. 查看当前数据统计
    logger.info("\n步骤1: 查看更新前的数据统计")
    stats_before = market_service.get_statistics()
    logger.info(f"  总记录数: {stats_before['total_records']}")
    logger.info(f"  股票数量: {stats_before['stock_count']}")
    logger.info(f"  最早日期: {stats_before['earliest_date']}")
    logger.info(f"  最晚日期: {stats_before['latest_date']}")
    
    # 2. 查看某只股票的最新数据
    test_code = '000001'
    logger.info(f"\n步骤2: 查看股票 {test_code} 更新前的最新数据")
    latest_before = market_service.get_latest_data(test_code)
    if latest_before:
        logger.info(f"  最新日期: {latest_before['trade_date']}")
        logger.info(f"  收盘价: {latest_before['close']}")
    else:
        logger.warning(f"  股票 {test_code} 暂无数据")
    
    # 3. 执行增量更新（更新最近5天的数据）
    logger.info("\n步骤3: 执行增量更新（最近5天）")
    logger.info("提示: 这将更新所有股票最近5天的行情数据")
    
    # 如果数据库为空，先提示用户
    if stats_before['total_records'] == 0:
        logger.warning("数据库为空，建议先执行全量导入")
        response = input("\n是否先导入10只股票的历史数据？(y/n): ")
        if response.lower() == 'y':
            logger.info("\n正在导入测试数据...")
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            
            result = market_service.import_all_history(
                start_date=start_date,
                end_date=end_date,
                limit=10
            )
            
            if result['success']:
                logger.info(f"✓ 导入成功！总记录数: {result['total_records']}")
            else:
                logger.error("✗ 导入失败")
                return
    
    # 询问是否执行增量更新
    response = input("\n是否执行增量更新测试？(y/n): ")
    if response.lower() != 'y':
        logger.info("取消增量更新测试")
        return
    
    # 执行增量更新
    logger.info("\n开始增量更新...")
    update_result = market_service.update_recent_data(days=5)
    
    if update_result['success']:
        logger.info("\n" + "=" * 60)
        logger.info("✓ 增量更新完成！")
        logger.info("=" * 60)
        logger.info(f"总股票数: {update_result['total_stocks']}")
        logger.info(f"成功: {update_result['success_count']}")
        logger.info(f"失败: {update_result['fail_count']}")
        logger.info(f"总记录数: {update_result['total_records']}")
        logger.info(f"耗时: {update_result['duration']:.2f}秒")
        logger.info(f"日期范围: {update_result['date_range']}")
        
        # 4. 查看更新后的数据统计
        logger.info("\n步骤4: 查看更新后的数据统计")
        stats_after = market_service.get_statistics()
        logger.info(f"  总记录数: {stats_after['total_records']}")
        logger.info(f"  股票数量: {stats_after['stock_count']}")
        logger.info(f"  最早日期: {stats_after['earliest_date']}")
        logger.info(f"  最晚日期: {stats_after['latest_date']}")
        
        # 5. 对比更新前后的变化
        logger.info("\n步骤5: 对比更新前后的变化")
        record_diff = stats_after['total_records'] - stats_before['total_records']
        logger.info(f"  记录数变化: {record_diff:+d}")
        
        # 6. 查看某只股票更新后的最新数据
        logger.info(f"\n步骤6: 查看股票 {test_code} 更新后的最新数据")
        latest_after = market_service.get_latest_data(test_code)
        if latest_after:
            logger.info(f"  最新日期: {latest_after['trade_date']}")
            logger.info(f"  收盘价: {latest_after['close']}")
            
            if latest_before:
                if latest_after['trade_date'] != latest_before['trade_date']:
                    logger.info(f"  ✓ 数据已更新（从 {latest_before['trade_date']} 到 {latest_after['trade_date']}）")
                else:
                    logger.info(f"  数据日期未变化（可能已是最新）")
        
        # 7. 查询最近5天的数据
        logger.info(f"\n步骤7: 查询股票 {test_code} 最近5天的数据")
        recent_df = market_service.get_stock_data(test_code, limit=5)
        if not recent_df.empty:
            logger.info(f"\n{recent_df.to_string()}")
        
        # 显示失败的股票（如果有）
        if update_result['fail_count'] > 0:
            logger.warning(f"\n有 {update_result['fail_count']} 只股票更新失败")
            if update_result['failed_stocks']:
                logger.warning("失败的股票列表（前5个）:")
                for stock in update_result['failed_stocks'][:5]:
                    logger.warning(f"  {stock['code']} - {stock['name']}: {stock['reason']}")
    else:
        logger.error(f"✗ 增量更新失败: {update_result.get('message', '未知错误')}")


def main():
    """主函数"""
    try:
        # 加载配置
        config = get_config()
        
        # 初始化日志系统
        setup_logging(config)
        logger = get_logger(__name__)
        
        logger.info("=" * 60)
        logger.info("股票分析系统 - 历史行情数据增量更新测试")
        logger.info("=" * 60)
        
        # 显示配置信息
        logger.info(f"数据源类型: {config.get('datasource.type')}")
        logger.info(f"SQLite数据库: {config.get('database.sqlite_path')}")
        logger.info(f"DuckDB数据库: {config.get('database.duckdb_path')}")
        
        # 初始化数据库
        sqlite_db = get_sqlite_db()
        duckdb = get_duckdb()
        logger.info("数据库初始化完成")
        
        # 测试增量更新功能
        test_incremental_update()
        
        logger.info("\n" + "=" * 60)
        logger.info("测试完成")
        logger.info("=" * 60)
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
