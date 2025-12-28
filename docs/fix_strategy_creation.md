# 策略创建问题修复总结

## 问题描述

### 问题1：不同用户不能使用相同的策略名称
- **现象**：新用户创建策略时，因为名字与其他用户的策略相同，导致创建失败
- **原因**：
  1. 数据库层面：`strategies` 表的 `name` 字段有全局 `UNIQUE` 约束
  2. 代码层面：检查策略名称是否重复时，没有添加 `user_id` 条件

### 问题2：前端一直显示"正在创建策略…"弹窗
- **现象**：策略创建失败后，前端加载弹窗不关闭，且不显示具体错误信息
- **原因**：前端错误处理逻辑不完善，`hideLoading()` 被调用但错误信息未正确传递

## 修复方案

### 1. 数据库迁移

创建了数据库迁移脚本，修改表结构：
- 删除 `name` 字段的全局唯一索引 `idx_name`
- 添加 `user_id` 字段（如果不存在）
- 添加 `(name, user_id)` 组合唯一索引 `idx_name_user`
- 添加 `user_id` 的外键约束和索引

**执行迁移**：
```bash
python3 scripts/migrate_strategy_name_unique.py
```

**迁移后的表结构**：
```sql
CREATE TABLE strategies (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(500) NOT NULL,
  user_id INT NOT NULL,
  description TEXT,
  config TEXT NOT NULL,
  enabled TINYINT(1) DEFAULT 1,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  last_executed_at DATETIME,
  UNIQUE INDEX idx_name_user (name, user_id),
  INDEX idx_enabled (enabled),
  INDEX idx_user_id (user_id),
  CONSTRAINT fk_strategies_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

### 2. 后端代码修改

#### 修改 `app/services/strategy_service.py`

**创建策略时**：
```python
# 修改前：全局检查名称重复
existing = self.db.execute_query(
    "SELECT id FROM strategies WHERE name = ?",
    (name.strip(),)
)

# 修改后：只检查当前用户的策略名称
existing = self.db.execute_query(
    "SELECT id FROM strategies WHERE name = ? AND user_id = ?",
    (name.strip(), user_id)
)
```

**更新策略时**：
```python
# 修改前：全局检查名称冲突
existing = self.db.execute_query(
    "SELECT id FROM strategies WHERE name = ? AND id != ?",
    (name.strip(), strategy_id)
)

# 修改后：只检查当前用户的策略名称冲突
existing = self.db.execute_query(
    "SELECT id FROM strategies WHERE name = ? AND id != ? AND user_id = ?",
    (name.strip(), strategy_id, user_id)
)
```

#### 修改 `app/api/routes/strategy_routes.py`

在创建策略前先检查名称重复，返回更友好的错误信息：
```python
# 检查策略名称是否已存在（同一用户下）
existing_strategy = strategy_service.get_strategy_by_name(data['name'], user_id=user_id)
if existing_strategy:
    return jsonify({
        'success': False,
        'error': '策略名称已存在，请使用其他名称'
    }), 400
```

### 3. 前端代码修改

#### 修改 `app/templates/strategies/form.html`

优化错误处理逻辑，确保错误信息能正确显示：
```javascript
apiRequest(url, method, data,
    function(response) {
        hideLoading();
        showMessage(isEdit ? '策略更新成功' : '策略创建成功', 'success');
        setTimeout(function() {
            window.location.href = '/strategies';
        }, 1000);
    },
    function(response) {
        // apiRequest 函数已经显示了错误信息，这里只需要关闭加载弹窗
        hideLoading();
    }
);
```

## 修复效果

### 问题1修复效果
✅ **不同用户现在可以使用相同的策略名称**
- 用户 A 可以创建策略"大涨策略"
- 用户 B 也可以创建策略"大涨策略"
- 同一用户下的策略名称仍然必须唯一

### 问题2修复效果
✅ **前端正确显示错误信息**
- 创建策略失败时，显示具体的错误信息（如"策略名称已存在，请使用其他名称"）
- 加载弹窗正确关闭
- 用户体验得到改善

## 验证结果

从日志中可以看到修复成功：

```
2025-12-28 16:00:51,247 - 策略创建成功: 测试策略 22-大涨后站稳5日线 (ID: 2, User: 6)
2025-12-28 16:00:51,247 - "POST /api/strategies HTTP/1.1" 201 -
```

## 相关文件

### 修改的文件
1. `app/services/strategy_service.py` - 策略服务层
2. `app/api/routes/strategy_routes.py` - 策略API路由
3. `app/templates/strategies/form.html` - 策略表单前端

### 新增的文件
1. `scripts/migrate_strategy_name_unique.sql` - SQL迁移脚本
2. `scripts/migrate_strategy_name_unique.py` - Python迁移脚本
3. `docs/fix_strategy_creation.md` - 本文档

## 注意事项

1. **数据库迁移已执行完成**，无需重复执行
2. 如果需要回滚，需要：
   - 删除 `idx_name_user` 索引
   - 删除 `user_id` 字段（或重置为默认值）
   - 恢复 `idx_name` 全局唯一索引
3. 现在的策略名称是"用户级唯一"，即同一用户下的策略名称不能重复

## 后续建议

1. 考虑为策略添加更详细的验证逻辑（如名称格式、长度等）
2. 在前端实时检查策略名称是否可用（防抖输入框）
3. 添加策略分类/标签功能，方便用户管理大量策略
