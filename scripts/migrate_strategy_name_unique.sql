-- 数据库迁移脚本：允许不同用户使用相同的策略名称
-- 移除 strategies 表的 name 全局唯一索引，添加 (name, user_id) 组合唯一索引

-- 步骤1：删除全局的 name 唯一索引
ALTER TABLE strategies DROP INDEX name;

-- 步骤2：添加 (name, user_id) 组合唯一索引
ALTER TABLE strategies ADD UNIQUE INDEX idx_name_user (name, user_id);

-- 步骤3：添加 user_id 字段（如果还没有的话）
-- 注意：如果已有 user_id 字段，这一步会跳过
ALTER TABLE strategies ADD COLUMN IF NOT EXISTS user_id INT NOT NULL DEFAULT 1 COMMENT '所属用户ID';

-- 步骤4：添加 user_id 的外键约束（关联到 users 表）
ALTER TABLE strategies ADD CONSTRAINT fk_strategies_user 
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- 步骤5：添加 user_id 的索引以提高查询性能
ALTER TABLE strategies ADD INDEX idx_user_id (user_id);

-- 显示修改后的表结构
DESCRIBE strategies;

-- 显示索引
SHOW INDEX FROM strategies;
