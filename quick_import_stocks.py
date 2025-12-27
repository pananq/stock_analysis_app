"""快速导入股票基础数据"""
from app.models import get_sqlite_db, get_duckdb

# 从DuckDB获取股票代码
duckdb = get_duckdb()
result = duckdb.execute_query('SELECT DISTINCT code FROM daily_market ORDER BY code')
stock_codes = [row['code'] for row in result]

print(f"从DuckDB获取到 {len(stock_codes)} 只股票")

# 插入到SQLite
sqlite_db = get_sqlite_db()
success_count = 0

for code in stock_codes:
    try:
        sqlite_db.execute_update(
            'INSERT OR IGNORE INTO stocks (code, name, market_type) VALUES (?, ?, ?)',
            (code, f'股票{code}', 'A股')
        )
        success_count += 1
    except Exception as e:
        print(f'插入失败 {code}: {e}')

print(f'成功导入 {success_count} 只股票到SQLite')
