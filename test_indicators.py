"""
测试技术指标计算功能
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
from app.indicators import TechnicalIndicators


def test_technical_indicators():
    """测试技术指标计算功能"""
    logger = get_logger(__name__)
    
    logger.info("=" * 60)
    logger.info("测试技术指标计算功能")
    logger.info("=" * 60)
    
    # 获取行情数据服务
    market_service = get_market_data_service()
    
    # 1. 获取测试股票数据
    test_code = '000001'
    logger.info(f"\n步骤1: 获取股票 {test_code} 的历史数据（最近60天）")
    
    df = market_service.get_stock_data(test_code, limit=60)
    
    if df.empty:
        logger.error(f"股票 {test_code} 没有数据，请先导入数据")
        return
    
    logger.info(f"  获取到 {len(df)} 条数据")
    logger.info(f"  日期范围: {df['trade_date'].min()} 至 {df['trade_date'].max()}")
    
    # 显示原始数据样例
    logger.info("\n原始数据样例（最近5天）:")
    logger.info(df.head().to_string())
    
    # 2. 测试移动平均线计算
    logger.info("\n步骤2: 测试移动平均线计算")
    df_with_ma = TechnicalIndicators.calculate_ma(df, periods=[5, 10, 20, 30, 60])
    
    logger.info("  计算的均线列:")
    ma_columns = [col for col in df_with_ma.columns if col.startswith('ma_')]
    logger.info(f"  {ma_columns}")
    
    # 显示带均线的数据
    logger.info("\n带均线的数据（最近5天）:")
    display_cols = ['trade_date', 'close', 'ma_5', 'ma_10', 'ma_20']
    logger.info(df_with_ma[display_cols].head().to_string())
    
    # 3. 测试涨跌幅计算
    logger.info("\n步骤3: 测试涨跌幅计算")
    df_with_change = TechnicalIndicators.calculate_change_pct(df_with_ma)
    df_with_change = TechnicalIndicators.calculate_change_amount(df_with_change)
    
    logger.info("\n带涨跌幅的数据（最近5天）:")
    display_cols = ['trade_date', 'close', 'change_amount', 'change_pct']
    logger.info(df_with_change[display_cols].head().to_string())
    
    # 4. 测试成交量均线计算
    logger.info("\n步骤4: 测试成交量均线计算")
    df_with_vol_ma = TechnicalIndicators.calculate_volume_ma(df_with_change, periods=[5, 10, 20])
    
    logger.info("\n带成交量均线的数据（最近5天）:")
    display_cols = ['trade_date', 'volume', 'volume_ma_5', 'volume_ma_10']
    logger.info(df_with_vol_ma[display_cols].head().to_string())
    
    # 5. 测试振幅计算
    logger.info("\n步骤5: 测试振幅计算")
    df_with_amp = TechnicalIndicators.calculate_amplitude(df_with_vol_ma)
    
    logger.info("\n带振幅的数据（最近5天）:")
    display_cols = ['trade_date', 'high', 'low', 'close', 'amplitude']
    logger.info(df_with_amp[display_cols].head().to_string())
    
    # 6. 测试价格是否在均线之上
    logger.info("\n步骤6: 测试价格是否在均线之上")
    df_with_check = TechnicalIndicators.check_above_ma(df_with_amp, ma_period=5, consecutive_days=3)
    
    logger.info("\n检查价格是否连续3天在5日均线之上:")
    display_cols = ['trade_date', 'close', 'ma_5', 'above_ma_5_3days']
    logger.info(df_with_check[display_cols].head(10).to_string())
    
    # 统计连续3天在5日均线之上的天数
    above_count = df_with_check['above_ma_5_3days'].sum()
    logger.info(f"\n  连续3天在5日均线之上的天数: {above_count}")
    
    # 7. 测试查找大涨日
    logger.info("\n步骤7: 测试查找大涨日（涨幅>8%）")
    big_rise_days = TechnicalIndicators.find_big_rise_days(df_with_check, threshold=8.0)
    
    if not big_rise_days.empty:
        logger.info(f"  找到 {len(big_rise_days)} 个大涨日:")
        display_cols = ['trade_date', 'close', 'change_pct']
        logger.info(big_rise_days[display_cols].to_string())
    else:
        logger.info("  未找到涨幅超过8%的交易日")
    
    # 8. 测试一次性计算所有基础指标
    logger.info("\n步骤8: 测试一次性计算所有基础指标")
    df_all = TechnicalIndicators.calculate_all_basic_indicators(df)
    
    logger.info(f"  计算后的列数: {len(df_all.columns)}")
    logger.info(f"  所有列名: {list(df_all.columns)}")
    
    # 显示完整指标数据
    logger.info("\n完整指标数据（最近3天）:")
    logger.info(df_all.head(3).to_string())
    
    # 9. 测试策略场景：查找大涨后连续3天在5日均线之上的情况
    logger.info("\n步骤9: 测试策略场景")
    logger.info("  场景: 某日涨幅>8%，随后3天收盘价均高于5日均线")
    
    # 先计算所有指标
    df_strategy = TechnicalIndicators.calculate_all_basic_indicators(df)
    
    # 查找大涨日
    big_rise_mask = df_strategy['change_pct'] >= 8.0
    
    if big_rise_mask.any():
        # 获取大涨日的索引
        big_rise_indices = df_strategy[big_rise_mask].index.tolist()
        
        logger.info(f"  找到 {len(big_rise_indices)} 个大涨日")
        
        # 检查每个大涨日后的3天是否都在5日均线之上
        matched_dates = []
        for idx in big_rise_indices:
            # 获取大涨日的日期
            rise_date = df_strategy.loc[idx, 'trade_date']
            
            # 检查后续3天
            next_3_days = df_strategy.loc[idx:idx+3]
            
            if len(next_3_days) >= 4:  # 包括大涨日本身
                # 检查后3天（不包括大涨日）是否都在5日均线之上
                next_3_days = next_3_days.iloc[1:4]
                
                if 'ma_5' in next_3_days.columns:
                    all_above = (next_3_days['close'] > next_3_days['ma_5']).all()
                    
                    if all_above:
                        matched_dates.append(rise_date)
                        logger.info(f"    ✓ {rise_date} 符合条件")
        
        if matched_dates:
            logger.info(f"\n  共找到 {len(matched_dates)} 个符合策略的日期")
        else:
            logger.info("\n  未找到符合策略的日期")
    else:
        logger.info("  未找到涨幅超过8%的交易日")
    
    logger.info("\n" + "=" * 60)
    logger.info("✓ 技术指标计算测试完成！")
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
        logger.info("股票分析系统 - 技术指标计算测试")
        logger.info("=" * 60)
        
        # 初始化数据库
        sqlite_db = get_sqlite_db()
        duckdb = get_duckdb()
        logger.info("数据库初始化完成")
        
        # 测试技术指标计算
        test_technical_indicators()
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
