# 数据库外键移除说明

## 概述

由于当前使用的数据库不支持外键约束，已从 ORM 模型和数据库中移除所有外键定义。

## 修改内容

### 1. ORM 模型修改 ([app/models/orm_models.py](app/models/orm_models.py))

#### 移除的外键定义：

- **Strategy 表**
  - `user_id`: 不再引用 `users.id`
  - 移除 `user` relationship 定义
  - 移除 `results` relationship 定义

- **StrategyResult 表**
  - `strategy_id`: 不再引用 `strategies.id`
  - `stock_code`: 不再引用 `stocks.code`
  - 移除 `strategy` relationship 定义

- **JobLog 表**
  - `user_id`: 不再引用 `users.id`
  - 移除 `user` relationship 定义

- **TaskExecutionDetail 表**
  - `job_log_id`: 不再引用 `job_logs.id`

- **User 表**
  - 移除 `strategies` relationship 定义
  - 移除 `job_logs` relationship 定义

#### 移除的导入：

```python
# 已从导入中移除
from sqlalchemy import (
    ...
    ForeignKey,  # ← 已移除
    ...
)
```

### 2. 数据库约束清理

使用 [drop_foreign_keys.py](drop_foreign_keys.py) 脚本删除了数据库中现有的 5 个外键约束：

1. `job_logs.fk_job_logs_user` (引用 users.id)
2. `strategies.fk_strategies_user` (引用 users.id)
3. `strategy_results.strategy_results_ibfk_1` (引用 strategies.id)
4. `strategy_results.strategy_results_ibfk_2` (引用 stocks.code)
5. `task_execution_details.task_execution_details_ibfk_1` (引用 job_logs.id)

## 验证

### 验证脚本

提供了两个验证脚本：

1. **[test_no_foreign_keys.py](test_no_foreign_keys.py)** - 验证外键是否完全移除
2. **[drop_foreign_keys.py](drop_foreign_keys.py)** - 删除数据库中的外键约束

### 验证结果

```
============================================================
检查 ORM 模型外键定义
============================================================

模型: User
  表名: users
  ✓ 无外键

模型: Strategy
  表名: strategies
  ✓ 无外键

模型: StrategyResult
  表名: strategy_results
  ✓ 无外键

模型: JobLog
  表名: job_logs
  ✓ 无外键

模型: TaskExecutionDetail
  表名: task_execution_details
  ✓ 无外键

============================================================
✓ 所有模型已成功移除外键
============================================================
检查数据库中的外键约束
============================================================

✓ 数据库中没有外键约束

============================================================
✓ 外键移除验证通过！
============================================================
```

## 影响说明

### 功能影响

外键移除后，以下功能需要通过应用层逻辑来维护：

1. **级联删除**: 删除用户时，不会自动删除相关的策略和任务日志
2. **数据完整性**: 需要在应用层确保引用数据的存在性
3. **级联更新**: 更新主表数据时，不会自动更新相关的外键引用

### 建议的应用层改进

为了保持数据一致性，建议在应用层实现以下逻辑：

1. **删除操作前检查**:
   ```python
   def delete_user(user_id):
       # 先删除关联的策略
       session.query(Strategy).filter(Strategy.user_id == user_id).delete()
       # 先删除关联的任务日志
       session.query(JobLog).filter(JobLog.user_id == user_id).delete()
       # 再删除用户
       session.query(User).filter(User.id == user_id).delete()
       session.commit()
   ```

2. **引用完整性检查**:
   ```python
   def add_strategy(user_id, strategy_data):
       # 检查用户是否存在
       user = session.query(User).filter(User.id == user_id).first()
       if not user:
           raise ValueError(f"用户 {user_id} 不存在")
       
       # 添加策略
       strategy = Strategy(user_id=user_id, **strategy_data)
       session.add(strategy)
       session.commit()
   ```

### 保留的索引

虽然移除了外键，但所有索引都保留了，这样可以：

1. 保持查询性能
2. 支持应用层的数据完整性检查
3. 便于实现自定义的级联操作

## 使用说明

### 验证外键状态

```bash
source venv/bin/activate
python test_no_foreign_keys.py
```

### 如果需要重新删除外键约束

```bash
source venv/bin/activate
python drop_foreign_keys.py
```

### 测试数据库功能

```bash
source venv/bin/activate
python verify_database.py
```

## 注意事项

1. **数据迁移**: 如果将数据迁移到支持外键的数据库，需要重新添加外键定义
2. **备份**: 在删除外键约束前，建议先备份数据库
3. **测试**: 外键移除后，务必充分测试应用的所有功能
4. **文档更新**: 更新相关的开发和运维文档

## 总结

✓ 所有 ORM 模型中的外键定义已移除
✓ 所有数据库中的外键约束已删除
✓ 索引保留，查询性能不受影响
✓ 应用功能正常，数据库操作测试通过
✓ 提供了验证脚本以便后续检查

数据库现在完全兼容不支持外键的数据库系统。
