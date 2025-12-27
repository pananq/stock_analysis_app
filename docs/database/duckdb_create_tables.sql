-- ============================================
-- DuckDB 数据库建表SQL脚本
-- 数据库名称: market_data.duckdb
-- 用途: 股票分析系统 - 历史行情数据库
-- ============================================

-- ============================================
-- 1. daily_market 表 - 股票日线行情数据表
-- ============================================
CREATE TABLE IF NOT EXISTS daily_market (
    code VARCHAR NOT NULL,
    trade_date DATE NOT NULL,
    open DECIMAL(10, 2),
    close DECIMAL(10, 2),
    high DECIMAL(10, 2),
    low DECIMAL(10, 2),
    volume BIGINT,
    amount DECIMAL(20, 2),
    change_pct DECIMAL(10, 2),
    turnover_rate DECIMAL(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (code, trade_date)
);

-- ============================================
-- 创建索引以优化查询性能
-- ============================================

-- 按股票代码索引
CREATE INDEX IF NOT EXISTS idx_daily_market_code 
ON daily_market(code);

-- 按交易日期索引
CREATE INDEX IF NOT EXISTS idx_daily_market_date 
ON daily_market(trade_date);

-- 按股票代码和交易日期复合索引
CREATE INDEX IF NOT EXISTS idx_daily_market_code_date 
ON daily_market(code, trade_date);

-- ============================================
-- 示例数据插入（可选）
-- ============================================

-- 插入示例行情数据
-- INSERT INTO daily_market (code, trade_date, open, close, high, low, volume, amount, change_pct, turnover_rate)
-- VALUES 
--     ('000001', '2025-12-26', 10.50, 10.80, 10.95, 10.45, 1000000, 10800000.00, 2.86, 1.5),
--     ('000002', '2025-12-26', 8.20, 8.35, 8.40, 8.15, 800000, 6680000.00, 1.83, 1.2),
--     ('600000', '2025-12-26', 5.60, 5.75, 5.80, 5.55, 2000000, 11500000.00, 2.68, 1.8);

-- ============================================
-- 常用查询示例
-- ============================================

-- 1. 查询某只股票的最新N条数据
-- SELECT * 
-- FROM daily_market 
-- WHERE code = '000001' 
-- ORDER BY trade_date DESC 
-- LIMIT 100;

-- 2. 查询某日期的所有股票数据
-- SELECT * 
-- FROM daily_market 
-- WHERE trade_date = '2025-12-26'
-- ORDER BY code;

-- 3. 查询某日期范围的某只股票数据
-- SELECT * 
-- FROM daily_market 
-- WHERE code = '000001' 
--   AND trade_date BETWEEN '2025-01-01' AND '2025-12-26'
-- ORDER BY trade_date;

-- 4. 计算移动平均线（5日、10日、20日）
-- SELECT 
--     code,
--     trade_date,
--     close,
--     AVG(close) OVER (
--         PARTITION BY code 
--         ORDER BY trade_date 
--         ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
--     ) as ma5,
--     AVG(close) OVER (
--         PARTITION BY code 
--         ORDER BY trade_date 
--         ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
--     ) as ma10,
--     AVG(close) OVER (
--         PARTITION BY code 
--         ORDER BY trade_date 
--         ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
--     ) as ma20
-- FROM daily_market
-- WHERE code = '000001'
-- ORDER BY trade_date;

-- 5. 查询涨幅最大的N只股票
-- SELECT 
--     code,
--     trade_date,
--     close,
--     change_pct,
--     volume
-- FROM daily_market
-- WHERE trade_date = '2025-12-26'
-- ORDER BY change_pct DESC
-- LIMIT 20;

-- 6. 查询成交额最大的N只股票
-- SELECT 
--     code,
--     trade_date,
--     close,
--     amount,
--     change_pct
-- FROM daily_market
-- WHERE trade_date = '2025-12-26'
-- ORDER BY amount DESC
-- LIMIT 20;

-- 7. 统计每日市场概况
-- SELECT 
--     trade_date,
--     COUNT(*) as stock_count,
--     AVG(change_pct) as avg_change_pct,
--     SUM(amount) as total_amount,
--     SUM(volume) as total_volume
-- FROM daily_market
-- WHERE trade_date >= '2025-12-01'
-- GROUP BY trade_date
-- ORDER BY trade_date DESC;

-- 8. 查询连续上涨的股票
-- SELECT 
--     code,
--     trade_date,
--     close,
--     change_pct,
--     LEAD(change_pct) OVER (PARTITION BY code ORDER BY trade_date) as next_change_pct
-- FROM daily_market
-- WHERE trade_date >= '2025-12-20'
--   AND change_pct > 0
-- ORDER BY code, trade_date;

-- 9. 查询成交量异常放大的股票
-- SELECT 
--     code,
--     trade_date,
--     close,
--     volume,
--     amount,
--     AVG(volume) OVER (
--         PARTITION BY code 
--         ORDER BY trade_date 
--         ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
--     ) as avg_volume_10,
--     volume / AVG(volume) OVER (
--         PARTITION BY code 
--         ORDER BY trade_date 
--         ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
--     ) as volume_ratio
-- FROM daily_market
-- WHERE trade_date = '2025-12-26'
--   AND volume > 0
-- ORDER BY volume_ratio DESC
-- LIMIT 20;

-- 10. 导出数据到CSV
-- COPY (
--     SELECT * 
--     FROM daily_market 
--     WHERE code = '000001' 
--     ORDER BY trade_date DESC
-- ) TO '/tmp/000001_daily.csv' 
-- WITH (FORMAT CSV, HEADER);

-- ============================================
-- 数据维护命令
-- ============================================

-- 更新统计信息，优化查询性能
-- PRAGMA analyze;

-- 优化数据库，回收空间
-- VACUUM;

-- 查看表结构
-- DESCRIBE daily_market;

-- 查看表的统计信息
-- PRAGMA table_info('daily_market');

-- 查看索引信息
-- PRAGMA show_indexes('daily_market');

-- ============================================
-- 性能优化建议
-- ============================================

-- 1. 使用分区表（DuckDB支持）
-- CREATE TABLE daily_market_partitioned (
--     code VARCHAR,
--     trade_date DATE,
--     open DECIMAL(10, 2),
--     close DECIMAL(10, 2),
--     high DECIMAL(10, 2),
--     low DECIMAL(10, 2),
--     volume BIGINT,
--     amount DECIMAL(20, 2),
--     change_pct DECIMAL(10, 2),
--     turnover_rate DECIMAL(10, 2),
--     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
-- ) 
-- PARTITION BY LIST (substr(code, 1, 3));

-- 2. 使用列式存储（DuckDB默认）
-- 3. 使用压缩（DuckDB自动压缩）
-- 4. 使用并行查询（DuckDB自动并行）
