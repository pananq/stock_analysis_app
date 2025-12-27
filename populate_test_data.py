#!/usr/bin/env python3
"""
测试数据填充脚本
为DuckDB数据库创建示例数据，用于测试
"""
import pandas as pd
from datetime import datetime, timedelta
import random
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models.duckdb_manager import DuckDBManager
from app.utils.config import get_config


def populate_duckdb_test_data():
    """填充DuckDB测试数据"""
    print("开始填充DuckDB测试数据...")
    
    # 获取配置
    config = get_config()
    db_manager = DuckDBManager(config.get('database.duckdb_path'))
    
    # 创建示例数据
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 12, 20)
    date_range = pd.date_range(start_date, end_date)
    
    # 为10只股票创建数据
    test_stocks = [
        '000001.SZ', '000002.SZ', '000858.SZ', '002594.SZ', '300059.SZ',
        '600000.SH', '600519.SH', '601318.SH', '600036.SH', '688981.SH'
    ]
    all_data = []
    
    for stock_code in test_stocks:
        for date in date_range:
            base_price = 10 if stock_code.startswith(('000', '002', '300')) else 100
            
            # 模拟价格波动
            random.seed(f'{stock_code}_{date}'.encode())
            open_price = base_price * (0.95 + random.random() * 0.1)
            close_price = base_price * (0.95 + random.random() * 0.1)
            high_price = max(open_price, close_price) * (1 + random.random() * 0.02)
            low_price = min(open_price, close_price) * (1 - random.random() * 0.02)
            volume = int(1000000 * (0.5 + random.random()))
            amount = volume * close_price
            
            all_data.append({
                'code': stock_code,
                'trade_date': date,
                'open': round(open_price, 2),
                'high': round(high_price, 2),
                'low': round(low_price, 2),
                'close': round(close_price, 2),
                'volume': volume,
                'amount': round(amount, 2),
                'change_pct': round((close_price - base_price) / base_price * 100, 2),
                'turnover_rate': round(random.random() * 5, 2)
            })
    
    # 转换为DataFrame并写入DuckDB
    df = pd.DataFrame(all_data)
    print(f'创建 {len(df)} 条测试数据，覆盖 {len(test_stocks)} 只股票')
    
    # 插入数据
    inserted = db_manager.insert_dataframe('daily_market', df)
    print(f'✓ 成功插入 {inserted} 条数据')
    
    # 验证数据
    count = len(df['code'].unique())
    print(f'✓ 数据库中现在有 {count} 只股票的数据')
    
    return inserted


def populate_sqlite_test_data():
    """填充SQLite测试数据（添加示例策略）"""
    print("\n开始填充SQLite测试数据...")
    
    from app.models.sqlite_db import SQLiteDB
    from app.utils.config import get_config
    import json
    
    config = get_config()
    sqlite_db = SQLiteDB(config.get('database.sqlite_path'))
    
    # 添加示例策略
    strategies = [
        {
            'name': '5日均线突破',
            'description': '当股价突破5日均线时买入',
            'config': json.dumps({
                'ma_periods': 5,
                'min_change_pct': 2.0,
                'max_change_pct': 10.0,
                'observe_days': 3
            }),
            'enabled': 1
        },
        {
            'name': '回调买入',
            'description': '当股价从高点回调3%以上时买入',
            'config': json.dumps({
                'ma_periods': 10,
                'min_change_pct': -3.0,
                'max_change_pct': 0.0,
                'observe_days': 5
            }),
            'enabled': 1
        }
    ]
    
    for strategy_data in strategies:
        strategy_id = sqlite_db.insert_one('strategies', strategy_data)
        print(f'✓ 创建策略: {strategy_data["name"]} (ID: {strategy_id})')
    
    return len(strategies)


if __name__ == '__main__':
    try:
        # 填充DuckDB数据
        duckdb_count = populate_duckdb_test_data()
        
        # 填充SQLite数据
        sqlite_count = populate_sqlite_test_data()
        
        print("\n" + "="*50)
        print("测试数据填充完成！")
        print(f"  - DuckDB行情数据: {duckdb_count} 条")
        print(f"  - SQLite示例策略: {sqlite_count} 个")
        print("="*50)
        print("\n现在可以运行完整测试:")
        print("  python3 -m tests.run_tests")
        
    except Exception as e:
        print(f"❌ 错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
