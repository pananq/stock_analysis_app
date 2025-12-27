# DuckDB 数据库 Schema 说明

## 数据库概述

- **数据库名称**: `market_data.duckdb`
- **数据库类型**: DuckDB
- **用途**: 存储股票历史行情数据（日线数据）
- **路径**: `./data/market_data.duckdb`
- **特点**: 
  - 支持OLAP分析，适合大规模数据分析
  - 支持列式存储，查询性能优异
  - 支持并行查询，多线程安全

---

## 表结构说明

### 1. daily_market（股票日线行情数据表）

存储A股市场所有股票的历史日线行情数据。

| 字段名 | 数据类型 | 约束 | 说明 |
|--------|---------|------|------|
| code | VARCHAR | NOT NULL, PRIMARY KEY | 股票代码（如：000001） |
| trade_date | DATE | NOT NULL, PRIMARY KEY | 交易日期 |
| open | DECIMAL(10, 2) | | 开盘价 |
| close | DECIMAL(10, 2) | | 收盘价 |
| high | DECIMAL(10, 2) | | 最高价 |
| low | DECIMAL(10, 2) | | 最低价 |
| volume | BIGINT | | 成交量（股） |
| amount | DECIMAL(20, 2) | | 成交额（元） |
| change_pct | DECIMAL(10, 2) | | 涨跌幅（%） |
| turnover_rate | DECIMAL(10, 2) | | 换手率（%） |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 数据创建时间 |

**主键**: (code, trade_date) - 联合主键

**索引**:
- `idx_daily_market_code`: code
- `idx_daily_market_date`: trade_date
- `idx_daily_market_code_date`: (code, trade_date)

---

## 数据库关系图

```
daily_market (股票日线行情)
    ├── code (股票代码)
    ├── trade_date (交易日期)
    ├── open/high/low/close (OHLC价格)
    ├── volume (成交量)
    ├── amount (成交额)
    ├── change_pct (涨跌幅)
    └── turnover_rate (换手率)
```

---

## 数据特点

1. **数据量**: 存储所有A股股票的历史日线数据，数据量较大（可达到数亿条记录）
2. **时间跨度**: 可追溯至股票上市日期
3. **更新频率**: 每个交易日更新一次
4. **数据来源**: 通过akshare等数据源获取

---

## 使用场景

1. **历史行情查询**: 查询任意股票的历史行情数据
2. **技术指标计算**: 计算移动平均线、MACD等技术指标
3. **数据分析**: 进行行情数据分析、回测等
4. **数据导出**: 支持导出为CSV、Parquet等格式

---

## 性能优化建议

1. **分区策略**: 建议按股票代码或日期进行分区，提高查询效率
2. **压缩存储**: DuckDB自动使用列式压缩，存储效率高
3. **索引优化**: 
   - `idx_daily_market_code_date` 索引是最重要的，支持按股票+日期查询
   - `idx_daily_market_date` 索引支持按日期范围查询所有股票
4. **查询优化**: 
   - 使用 WHERE 子句过滤日期范围
   - 使用 LIMIT 限制返回记录数
   - 使用聚合函数进行统计分析
5. **并发访问**: 使用线程锁控制并发写入，读取支持并发

---

## 常用查询示例

### 1. 查询某只股票的最新N条数据

```sql
SELECT * 
FROM daily_market 
WHERE code = '000001' 
ORDER BY trade_date DESC 
LIMIT 100;
```

### 2. 查询某日期的所有股票数据

```sql
SELECT * 
FROM daily_market 
WHERE trade_date = '2025-12-26';
```

### 3. 查询某日期范围的某只股票数据

```sql
SELECT * 
FROM daily_market 
WHERE code = '000001' 
  AND trade_date BETWEEN '2025-01-01' AND '2025-12-26'
ORDER BY trade_date;
```

### 4. 计算移动平均线（5日、10日、20日）

```sql
SELECT 
    code,
    trade_date,
    close,
    AVG(close) OVER (
        PARTITION BY code 
        ORDER BY trade_date 
        ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
    ) as ma5,
    AVG(close) OVER (
        PARTITION BY code 
        ORDER BY trade_date 
        ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
    ) as ma10,
    AVG(close) OVER (
        PARTITION BY code 
        ORDER BY trade_date 
        ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
    ) as ma20
FROM daily_market
WHERE code = '000001'
ORDER BY trade_date;
```

### 5. 查询涨幅最大的N只股票

```sql
SELECT 
    code,
    trade_date,
    close,
    change_pct,
    volume
FROM daily_market
WHERE trade_date = '2025-12-26'
ORDER BY change_pct DESC
LIMIT 20;
```

### 6. 查询成交额最大的N只股票

```sql
SELECT 
    code,
    trade_date,
    close,
    amount,
    change_pct
FROM daily_market
WHERE trade_date = '2025-12-26'
ORDER BY amount DESC
LIMIT 20;
```

### 7. 统计每日市场概况

```sql
SELECT 
    trade_date,
    COUNT(*) as stock_count,
    AVG(change_pct) as avg_change_pct,
    SUM(amount) as total_amount,
    SUM(volume) as total_volume
FROM daily_market
WHERE trade_date >= '2025-12-01'
GROUP BY trade_date
ORDER BY trade_date DESC;
```

### 8. 查询连续上涨的股票

```sql
SELECT 
    code,
    trade_date,
    close,
    change_pct,
    LEAD(change_pct) OVER (PARTITION BY code ORDER BY trade_date) as next_change_pct
FROM daily_market
WHERE trade_date >= '2025-12-20'
  AND change_pct > 0
ORDER BY code, trade_date;
```

### 9. 查询成交量异常放大的股票

```sql
SELECT 
    code,
    trade_date,
    close,
    volume,
    amount,
    AVG(volume) OVER (
        PARTITION BY code 
        ORDER BY trade_date 
        ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
    ) as avg_volume_10,
    volume / AVG(volume) OVER (
        PARTITION BY code 
        ORDER BY trade_date 
        ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
    ) as volume_ratio
FROM daily_market
WHERE trade_date = '2025-12-26'
  AND volume > 0
ORDER BY volume_ratio DESC
LIMIT 20;
```

### 10. 导出数据到CSV

```sql
COPY (
    SELECT * 
    FROM daily_market 
    WHERE code = '000001' 
    ORDER BY trade_date DESC
) TO '/tmp/000001_daily.csv' 
WITH (FORMAT CSV, HEADER);
```

---

## 数据维护建议

1. **定期备份**: 定期备份DuckDB数据库文件
2. **数据清理**: 定期清理过期的历史数据，保留必要的历史数据即可
3. **VACUUM**: 定期执行VACUUM命令优化数据库空间
4. **统计信息**: 定期更新统计信息，优化查询计划

```sql
-- 更新统计信息
PRAGMA analyze;

-- 优化数据库
VACUUM;
```

---

## 与SQLite的配合使用

- **SQLite**: 存储股票基础信息、策略配置、执行结果等元数据
- **DuckDB**: 存储历史行情数据，支持高效的OLAP查询

两者通过股票代码（code）进行关联，实现完整的股票分析功能。

---

## 性能特点

1. **列式存储**: 适合分析型查询，只读取需要的列
2. **向量化执行**: 利用SIMD指令加速查询
3. **并行查询**: 支持多线程并行执行查询
4. **内存映射**: 使用内存映射文件，减少I/O开销
5. **智能索引**: 自动选择最优索引策略
