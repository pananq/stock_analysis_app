-- ============================================
-- 8. users 表 - 用户表
-- ============================================
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '用户ID',
  `username` VARCHAR(50) NOT NULL COMMENT '用户名',
  `password_hash` VARCHAR(255) NOT NULL COMMENT '密码哈希',
  `role` VARCHAR(20) NOT NULL DEFAULT 'user' COMMENT '角色(admin/user)',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `last_login` DATETIME DEFAULT NULL COMMENT '最后登录时间',
  PRIMARY KEY (`id`),
  UNIQUE INDEX `idx_username` (`username`),
  INDEX `idx_role` (`role`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- ============================================
-- 数据迁移 - 插入默认管理员
-- ============================================
-- 注意：这里的密码哈希是 'admin123' 的 bcrypt 哈希值 (示例，实际应在应用层生成)
-- 为了方便迁移，这里先插入一个占位符，后续通过管理脚本重置
INSERT INTO `users` (`username`, `password_hash`, `role`) 
VALUES ('admin', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxwKc.60rScphF.1k1.1k1.1k1.1', 'admin');

-- 获取管理员ID
SET @admin_id = (SELECT id FROM users WHERE username = 'admin');

-- ============================================
-- 修改 strategies 表 - 添加 user_id
-- ============================================
-- 1. 添加列
ALTER TABLE `strategies` 
ADD COLUMN `user_id` INT DEFAULT NULL COMMENT '所属用户ID' AFTER `id`;

-- 2. 更新现有数据归属给管理员
UPDATE `strategies` SET `user_id` = @admin_id WHERE `user_id` IS NULL;

-- 3. 添加外键约束
ALTER TABLE `strategies`
ADD CONSTRAINT `fk_strategies_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;

-- 4. 添加索引
CREATE INDEX `idx_strategies_user_id` ON `strategies` (`user_id`);

-- ============================================
-- 修改 job_logs 表 - 添加 user_id
-- ============================================
-- 1. 添加列
ALTER TABLE `job_logs` 
ADD COLUMN `user_id` INT DEFAULT NULL COMMENT '所属用户ID' AFTER `id`;

-- 2. 更新现有数据归属给管理员
UPDATE `job_logs` SET `user_id` = @admin_id WHERE `user_id` IS NULL;

-- 3. 添加外键约束
ALTER TABLE `job_logs`
ADD CONSTRAINT `fk_job_logs_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;

-- 4. 添加索引
CREATE INDEX `idx_job_logs_user_id` ON `job_logs` (`user_id`);
