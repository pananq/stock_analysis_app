-- MySQL 8.0 建表 SQL 脚本
-- 股票分析系统数据库表结构
-- 字符集: utf8mb4
-- 排序规则: utf8mb4_unicode_ci
-- 存储引擎: InnoDB

-- 设置字符集
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ============================================
-- 1. stocks 表 - 股票基础信息表
-- ============================================
DROP TABLE IF EXISTS `stocks`;
CREATE TABLE `stocks` (
  `code` VARCHAR(20) NOT NULL COMMENT '股票代码',
  `name` VARCHAR(500) NOT NULL COMMENT '股票名称',
  `list_date` DATE DEFAULT NULL COMMENT '上市日期',
  `industry` VARCHAR(200) DEFAULT NULL COMMENT '所属行业',
  `market_type` VARCHAR(50) DEFAULT NULL COMMENT '市场类型',
  `status` VARCHAR(50) DEFAULT 'normal' COMMENT '股票状态',
  `earliest_data_date` DATE DEFAULT NULL COMMENT '最早数据日期',
  `latest_data_date` DATE DEFAULT NULL COMMENT '最近数据日期',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`code`),
  INDEX `idx_status` (`status`),
  INDEX `idx_industry` (`industry`),
  INDEX `idx_market_type` (`market_type`),
  INDEX `idx_earliest_data_date` (`earliest_data_date`),
  INDEX `idx_latest_data_date` (`latest_data_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='股票基础信息表';

-- ============================================
-- 2. strategies 表 - 策略配置表
-- ============================================
DROP TABLE IF EXISTS `strategies`;
CREATE TABLE `strategies` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '策略ID',
  `name` VARCHAR(500) NOT NULL COMMENT '策略名称',
  `description` TEXT COMMENT '策略描述',
  `config` TEXT NOT NULL COMMENT '策略配置（JSON格式）',
  `enabled` TINYINT(1) DEFAULT 1 COMMENT '是否启用（0/1）',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `last_executed_at` DATETIME DEFAULT NULL COMMENT '最后执行时间',
  PRIMARY KEY (`id`),
  UNIQUE INDEX `idx_name` (`name`),
  INDEX `idx_enabled` (`enabled`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='策略配置表';

-- ============================================
-- 3. strategy_results 表 - 策略执行结果表
-- ============================================
DROP TABLE IF EXISTS `strategy_results`;
CREATE TABLE `strategy_results` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '结果ID',
  `strategy_id` INT NOT NULL COMMENT '关联的策略ID',
  `stock_code` VARCHAR(20) NOT NULL COMMENT '股票代码',
  `trigger_date` DATE NOT NULL COMMENT '触发日期',
  `trigger_price` DECIMAL(10,4) DEFAULT NULL COMMENT '触发价格',
  `rise_percent` DECIMAL(10,4) DEFAULT NULL COMMENT '涨幅百分比',
  `result_data` TEXT COMMENT '结果详情数据（JSON格式）',
  `executed_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '执行时间',
  PRIMARY KEY (`id`),
  INDEX `idx_strategy_id` (`strategy_id`),
  INDEX `idx_stock_code` (`stock_code`),
  INDEX `idx_trigger_date` (`trigger_date`),
  INDEX `idx_executed_at` (`executed_at`),
  CONSTRAINT `fk_strategy_results_strategy` FOREIGN KEY (`strategy_id`) REFERENCES `strategies` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_strategy_results_stock` FOREIGN KEY (`stock_code`) REFERENCES `stocks` (`code`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='策略执行结果表';

-- ============================================
-- 4. system_logs 表 - 系统日志表
-- ============================================
DROP TABLE IF EXISTS `system_logs`;
CREATE TABLE `system_logs` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '日志ID',
  `timestamp` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '时间戳',
  `level` VARCHAR(50) NOT NULL COMMENT '日志级别',
  `module` VARCHAR(200) NOT NULL COMMENT '模块名称',
  `message` TEXT NOT NULL COMMENT '日志消息',
  `details` TEXT COMMENT '详细信息',
  PRIMARY KEY (`id`),
  INDEX `idx_timestamp` (`timestamp`),
  INDEX `idx_level` (`level`),
  INDEX `idx_module` (`module`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统日志表';

-- ============================================
-- 5. data_update_history 表 - 数据更新历史表
-- ============================================
DROP TABLE IF EXISTS `data_update_history`;
CREATE TABLE `data_update_history` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '历史记录ID',
  `update_type` VARCHAR(100) NOT NULL COMMENT '更新类型',
  `start_time` DATETIME NOT NULL COMMENT '开始时间',
  `end_time` DATETIME DEFAULT NULL COMMENT '结束时间',
  `total_count` INT DEFAULT 0 COMMENT '总记录数',
  `success_count` INT DEFAULT 0 COMMENT '成功记录数',
  `fail_count` INT DEFAULT 0 COMMENT '失败记录数',
  `status` VARCHAR(50) DEFAULT 'running' COMMENT '状态',
  `error_message` TEXT COMMENT '错误消息',
  PRIMARY KEY (`id`),
  INDEX `idx_update_type` (`update_type`),
  INDEX `idx_status` (`status`),
  INDEX `idx_start_time` (`start_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='数据更新历史表';

-- ============================================
-- 6. job_logs 表 - 定时任务执行日志表
-- ============================================
DROP TABLE IF EXISTS `job_logs`;
CREATE TABLE `job_logs` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '日志ID',
  `job_type` VARCHAR(100) NOT NULL COMMENT '任务类型',
  `job_name` VARCHAR(200) NOT NULL COMMENT '任务名称',
  `status` VARCHAR(50) NOT NULL COMMENT '执行状态',
  `started_at` DATETIME NOT NULL COMMENT '开始时间',
  `completed_at` DATETIME DEFAULT NULL COMMENT '完成时间',
  `duration` DECIMAL(10,4) DEFAULT NULL COMMENT '执行时长（秒）',
  `message` TEXT COMMENT '消息',
  `error` TEXT COMMENT '错误信息',
  PRIMARY KEY (`id`),
  INDEX `idx_job_type` (`job_type`),
  INDEX `idx_status` (`status`),
  INDEX `idx_started_at` (`started_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='定时任务执行日志表';

-- ============================================
-- 7. task_execution_details 表 - 任务执行详情表
-- ============================================
DROP TABLE IF EXISTS `task_execution_details`;
CREATE TABLE `task_execution_details` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '详情ID',
  `job_log_id` INT NOT NULL COMMENT '关联的任务日志ID',
  `task_type` VARCHAR(100) NOT NULL COMMENT '任务类型',
  `stock_code` VARCHAR(20) DEFAULT NULL COMMENT '股票代码',
  `stock_name` VARCHAR(500) DEFAULT NULL COMMENT '股票名称',
  `detail_type` VARCHAR(100) NOT NULL COMMENT '详情类型',
  `detail_data` TEXT NOT NULL COMMENT '详情数据',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  INDEX `idx_job_log_id` (`job_log_id`),
  INDEX `idx_task_type` (`task_type`),
  INDEX `idx_stock_code` (`stock_code`),
  INDEX `idx_detail_type` (`detail_type`),
  CONSTRAINT `fk_task_execution_details_job` FOREIGN KEY (`job_log_id`) REFERENCES `job_logs` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='任务执行详情表';

-- 恢复外键检查
SET FOREIGN_KEY_CHECKS = 1;

-- ============================================
-- 初始化数据（可选）
-- ============================================

-- 插入默认策略（可选）
-- INSERT INTO `strategies` (`name`, `description`, `config`, `enabled`) VALUES
-- ('默认策略', '默认的分析策略配置', '{"rise_threshold": 8.0, "observation_days": 3}', 1);

-- 显示表结构
SHOW TABLES;
