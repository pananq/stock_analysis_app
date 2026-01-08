-- ============================================
-- MySQL 数据库迁移脚本
-- 用于更新 strategy_results 表结构
-- 添加缺失的字段以支持新的策略执行结果
-- ============================================

-- 设置字符集
SET NAMES utf8mb4;

-- 备份现有数据
CREATE TABLE IF NOT EXISTS strategy_results_backup_20251230 AS 
SELECT * FROM strategy_results;

-- 添加缺失的字段
ALTER TABLE strategy_results 
ADD COLUMN IF NOT EXISTS stock_name VARCHAR(100) COMMENT '股票名称';

ALTER TABLE strategy_results 
ADD COLUMN IF NOT EXISTS trigger_pct_change DECIMAL(10,2) COMMENT '触发涨幅百分比';

ALTER TABLE strategy_results 
ADD COLUMN IF NOT EXISTS observation_days INT COMMENT '观察天数';

ALTER TABLE strategy_results 
ADD COLUMN IF NOT EXISTS ma_period INT COMMENT '均线周期';

ALTER TABLE strategy_results 
ADD COLUMN IF NOT EXISTS observation_result TEXT COMMENT '观察结果详情（JSON格式）';

ALTER TABLE strategy_results 
ADD COLUMN IF NOT EXISTS result_data TEXT COMMENT '结果数据（JSON格式）';

ALTER TABLE strategy_results 
ADD COLUMN IF NOT EXISTS created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间';

-- 为现有记录填充 stock_name（如果 stocks 表中存在）
UPDATE strategy_results sr
LEFT JOIN stocks s ON sr.stock_code = s.code
SET sr.stock_name = s.name
WHERE sr.stock_name IS NULL AND s.name IS NOT NULL;

-- 显示更新后的表结构
SHOW COLUMNS FROM strategy_results;

-- 查看现有数据
SELECT COUNT(*) as total_records FROM strategy_results;
SELECT COUNT(*) as records_with_stock_name FROM strategy_results WHERE stock_name IS NOT NULL;
