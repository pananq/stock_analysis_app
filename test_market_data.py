"""
测试历史行情数据导入功能
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.utils import get_config, setup_logging, get_logger
from app.models import get_sqlite_db, get_duckdb
from app.services import get_market_data_service


def test_market_data_service():
    """测试行情数据服务"""
    logger = get_logger(__name__)
    
    logger.info("=" * 60)
    logger.info("测试历史行情数据服务")
    logger.info("=" * 60)
    
    # 获取行情数据服务
    market_service = get_market_data_service()
    
    # 测试1: 获取统计信息
    logger.info("\n测试1: 获取当前数据统计")
    stats = market_service.get_statistics()
    logger.info(f"总记录数: {stats['total_records']}")
    logger.info(f"股票数量: {stats['stock_count']}")
    logger.info(f"最早日期: {stats['earliest_date']}")
    logger.info(f"最晚日期: {stats['latest_date']}")
    
    # 测试2: 查询特定股票数据
    test_code = '000001'  # 平安银行
    logger.info(f"\n测试2: 查询股票 {test_code} 的数据")
    
    # 获取数据日期范围
    date_range = market_service.get_data_date_range(test_code)
    if date_range:
        logger.info(f"  日期范围: {date_range['earliest_date']} 至 {date_range['latest_date']}")
        logger.info(f"  记录数: {date_range['record_count']}")
        
        # 获取最新数据
        latest = market_service.get_latest_data(test_code)
        if latest:
            logger.info(f"  最新数据:")
            logger.info(f"    日期: {latest['trade_date']}")
            logger.info(f"    开盘: {latest['open']}")
            logger.info(f"    收盘: {latest['close']}")
            logger.info(f"    最高: {latest['high']}")
            logger.info(f"    最低: {latest['low']}")
            logger.info(f"    成交量: {latest['volume']}")
    else:
        logger.info(f"  股票 {test_code} 暂无数据")
    
    # 询问是否执行小批量导入测试
    if stats['total_records'] == 0:
        logger.info("\n" + "=" * 60)
        logger.info("数据库为空，建议执行小批量导入测试")
        logger.info("=" * 60)
        response = input("\n是否导入10只股票的历史数据进行测试？(y/n): ")
        
        if response.lower() == 'y':
            logger.info("\n开始小批量导入测试（10只股票，最近1年数据）...")
            
            from datetime import datetime, timedelta
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            
            result = market_service.import_all_history(
                start_date=start_date,
                end_date=end_date,
                limit=10  # 只导入10只股票
            )
            
            if result['success']:
                logger.info(f"\n✓ 导入成功！")
                logger.info(f"  股票数: {result['total_stocks']}")
                logger.info(f"  成功: {result['success_count']}")
                logger.info(f"  失败: {result['fail_count']}")
                logger.info(f"  总记录数: {result['total_records']}")
                logger.info(f"  耗时: {result['duration']:.2f}秒")
                
                # 再次查询统计信息
                logger.info("\n导入后的统计信息:")
                stats = market_service.get_statistics()
                logger.info(f"  总记录数: {stats['total_records']}")
                logger.info(f"  股票数量: {stats['stock_count']}")
                logger.info(f"  日期范围: {stats['earliest_date']} 至 {stats['latest_date']}")
                
                # 查询第一只股票的数据
                logger.info("\n查询第一只股票的最新5条数据:")
                df = market_service.get_stock_data('000001', limit=5)
                if not df.empty:
                    logger.info(f"\n{df.to_string()}")
            else:
                logger.error(f"✗ 导入失败: {result.get('message', '未知错误')}")
    else:
        logger.info("\n数据库已有行情数据")
        logger.info("提示: 可以使用 update_recent_data() 方法进行增量更新")


def main():
    """主函数"""
    try:
        # 加载配置
        config = get_config()
        
        # 初始化日志系统
        setup_logging(config)
        logger = get_logger(__name__)
        
        logger.info("=" * 60)
        logger.info("股票分析系统 - 历史行情数据导入测试")
        logger.info("=" * 60)
        
        # 显示配置信息
        logger.info(f"数据源类型: {config.get('datasource.type')}")
        logger.info(f"SQLite数据库: {config.get('database.sqlite_path')}")
        logger.info(f"DuckDB数据库: {config.get('database.duckdb_path')}")
        
        # 初始化数据库
        sqlite_db = get_sqlite_db()
        duckdb = get_duckdb()
        logger.info("数据库初始化完成")
        
        # 测试行情数据服务
        test_market_data_service()
        
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
