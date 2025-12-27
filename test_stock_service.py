"""
测试股票服务功能
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.utils import get_config, setup_logging, get_logger
from app.models import get_sqlite_db, get_duckdb
from app.services import get_stock_service


def test_stock_service():
    """测试股票服务"""
    logger = get_logger(__name__)
    
    logger.info("=" * 60)
    logger.info("测试股票服务")
    logger.info("=" * 60)
    
    # 获取股票服务
    stock_service = get_stock_service()
    
    # 测试1: 获取股票数量
    logger.info("\n测试1: 获取当前股票数量")
    count = stock_service.get_stock_count()
    logger.info(f"当前数据库中有{count}只股票")
    
    # 测试2: 获取市场类型
    logger.info("\n测试2: 获取市场类型")
    market_types = stock_service.get_market_types()
    logger.info(f"市场类型: {market_types}")
    
    # 测试3: 查询股票列表（前10条）
    logger.info("\n测试3: 查询股票列表（前10条）")
    stocks = stock_service.get_stock_list(limit=10)
    for stock in stocks:
        logger.info(f"  {stock['code']} - {stock['name']} ({stock['market_type']})")
    
    # 测试4: 搜索股票
    logger.info("\n测试4: 搜索股票（关键词：平安）")
    results = stock_service.search_stocks("平安", limit=5)
    for stock in results:
        logger.info(f"  {stock['code']} - {stock['name']}")
    
    # 询问是否执行全量导入
    if count == 0:
        logger.info("\n" + "=" * 60)
        logger.info("数据库为空，建议执行全量导入")
        logger.info("=" * 60)
        response = input("\n是否执行全量导入股票列表？(y/n): ")
        
        if response.lower() == 'y':
            logger.info("\n开始全量导入股票列表...")
            result = stock_service.fetch_and_save_stock_list()
            
            if result['success']:
                logger.info(f"✓ 导入成功！")
                logger.info(f"  总数: {result['total']}")
                logger.info(f"  成功: {result['success_count']}")
                logger.info(f"  失败: {result['fail_count']}")
                logger.info(f"  耗时: {result['duration']:.2f}秒")
                
                # 再次查询股票列表
                logger.info("\n导入后的股票列表（前10条）:")
                stocks = stock_service.get_stock_list(limit=10)
                for stock in stocks:
                    logger.info(f"  {stock['code']} - {stock['name']} ({stock['market_type']})")
            else:
                logger.error(f"✗ 导入失败: {result['message']}")
    else:
        logger.info("\n数据库已有股票数据，可以使用增量更新功能")


def main():
    """主函数"""
    try:
        # 加载配置
        config = get_config()
        
        # 初始化日志系统
        setup_logging(config)
        logger = get_logger(__name__)
        
        logger.info("=" * 60)
        logger.info("股票分析系统 - 股票服务测试")
        logger.info("=" * 60)
        
        # 显示配置信息
        logger.info(f"数据源类型: {config.get('datasource.type')}")
        logger.info(f"SQLite数据库: {config.get('database.sqlite_path')}")
        logger.info(f"DuckDB数据库: {config.get('database.duckdb_path')}")
        
        # 初始化数据库
        sqlite_db = get_sqlite_db()
        duckdb = get_duckdb()
        logger.info("数据库初始化完成")
        
        # 测试股票服务
        test_stock_service()
        
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
