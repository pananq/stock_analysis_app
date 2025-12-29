-- ============================================
-- SQLite 数据库建表SQL脚本
-- 数据库名称: stock_analysis.db
-- 用途: 股票分析系统 - 基础信息数据库
-- ============================================

-- ============================================
-- 1. stocks 表 - 股票基础信息表
-- ============================================
CREATE TABLE IF NOT EXISTS stocks (
    code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    list_date TEXT,
    industry TEXT,
    market_type TEXT,
    status TEXT DEFAULT 'normal',
    earliest_data_date TEXT,
    latest_data_date TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_stocks_status 
ON stocks(status);

CREATE INDEX IF NOT EXISTS idx_stocks_industry 
ON stocks(industry);

CREATE INDEX IF NOT EXISTS idx_stocks_market_type 
ON stocks(market_type);

CREATE INDEX IF NOT EXISTS idx_stocks_earliest_data_date 
ON stocks(earliest_data_date);

CREATE INDEX IF NOT EXISTS idx_stocks_latest_data_date 
ON stocks(latest_data_date);

-- ============================================
-- 2. strategies 表 - 策略配置表
-- ============================================
CREATE TABLE IF NOT EXISTS strategies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    config TEXT NOT NULL,
    enabled INTEGER DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    last_executed_at TEXT
);

-- ============================================
-- 3. strategy_results 表 - 策略执行结果表
-- ============================================
CREATE TABLE IF NOT EXISTS strategy_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_id INTEGER NOT NULL,
    stock_code TEXT NOT NULL,
    trigger_date TEXT NOT NULL,
    trigger_price REAL,
    rise_percent REAL,
    result_data TEXT,
    executed_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (strategy_id) REFERENCES strategies(id) ON DELETE CASCADE,
    FOREIGN KEY (stock_code) REFERENCES stocks(code)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_strategy_results_strategy_id 
ON strategy_results(strategy_id);

CREATE INDEX IF NOT EXISTS idx_strategy_results_executed_at 
ON strategy_results(executed_at);

-- ============================================
-- 4. system_logs 表 - 系统日志表
-- ============================================
CREATE TABLE IF NOT EXISTS system_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    level TEXT NOT NULL,
    module TEXT NOT NULL,
    message TEXT NOT NULL,
    details TEXT
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_system_logs_timestamp 
ON system_logs(timestamp);

CREATE INDEX IF NOT EXISTS idx_system_logs_level 
ON system_logs(level);

-- ============================================
-- 5. data_update_history 表 - 数据更新历史表
-- ============================================
CREATE TABLE IF NOT EXISTS data_update_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    update_type TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT,
    total_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    fail_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'running',
    error_message TEXT
);

-- ============================================
-- 6. job_logs 表 - 定时任务执行日志表
-- ============================================
CREATE TABLE IF NOT EXISTS job_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_type TEXT NOT NULL,
    job_name TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    duration REAL,
    message TEXT,
    error TEXT
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_job_logs_job_type 
ON job_logs(job_type);

CREATE INDEX IF NOT EXISTS idx_job_logs_started_at 
ON job_logs(started_at);

-- ============================================
-- 7. task_execution_details 表 - 任务执行详细结果表
-- ============================================
CREATE TABLE IF NOT EXISTS task_execution_details (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_log_id INTEGER NOT NULL,
    task_type TEXT NOT NULL,
    stock_code TEXT,
    stock_name TEXT,
    detail_type TEXT NOT NULL,
    detail_data TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_log_id) REFERENCES job_logs(id) ON DELETE CASCADE
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_task_execution_details_job_log_id 
ON task_execution_details(job_log_id);

CREATE INDEX IF NOT EXISTS idx_task_execution_details_task_type 
ON task_execution_details(task_type);

CREATE INDEX IF NOT EXISTS idx_task_execution_details_stock_code 
ON task_execution_details(stock_code);

-- ============================================
-- 示例数据插入（可选）
-- ============================================

-- 插入示例策略
-- INSERT INTO strategies (name, description, config, enabled) 
-- VALUES (
--     '均线策略', 
--     '基于移动平均线的交易策略', 
--     '{"ma_short":5,"ma_long":20,"signal":"buy"}', 
--     1
-- );

-- 插入示例股票
-- INSERT INTO stocks (code, name, list_date, industry, market_type) 
-- VALUES 
--     ('000001', '平安银行', '1991-04-03', '银行', '主板'),
--     ('000002', '万科A', '1991-01-29', '房地产', '主板');

-- ============================================
-- 常用查询示例
-- ============================================

-- 查询所有启用的策略
-- SELECT * FROM strategies WHERE enabled = 1;

-- 查询某个策略的执行结果（最近10条）
-- SELECT sr.*, s.name as strategy_name 
-- FROM strategy_results sr 
-- JOIN strategies s ON sr.strategy_id = s.id 
-- WHERE sr.strategy_id = 1 
-- ORDER BY sr.executed_at DESC 
-- LIMIT 10;

-- 查询最近的系统日志
-- SELECT * FROM system_logs 
-- ORDER BY timestamp DESC 
-- LIMIT 100;

-- 查询最近的任务执行记录
-- SELECT * FROM job_logs 
-- ORDER BY started_at DESC 
-- LIMIT 20;

-- 查询数据更新历史
-- SELECT * FROM data_update_history 
-- ORDER BY start_time DESC 
-- LIMIT 50;

-- 查询某个任务执行的详细结果
-- SELECT ted.* 
-- FROM task_execution_details ted 
-- JOIN job_logs jl ON ted.job_log_id = jl.id 
-- WHERE jl.id = 1;
