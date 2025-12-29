# 数据库重试机制说明

## 概述

系统现已集成自动重试机制，当通过 ORM 访问数据库时，如果遇到连接池异常或数据库异常，系统会自动进行重试，提高系统的稳定性和可靠性。

## 重试机制特性

### 1. 自动重试

- **触发条件**: 当遇到数据库相关的异常时自动触发重试
- **最大重试次数**: 默认 3 次（可配置）
- **重试延迟**: 默认 0.5 秒，采用指数退避策略（0.5s → 1s → 2s）
- **退避因子**: 默认 2.0（每次重试延迟时间翻倍）

### 2. 支持的异常类型

重试机制会对以下异常类型进行重试：

- `pymysql.OperationalError` - MySQL 操作错误（如连接丢失、命令不同步）
- `pymysql.InterfaceError` - MySQL 接口错误
- `pymysql.DatabaseError` - MySQL 数据库错误
- `sqlalchemy.exc.OperationalError` - SQLAlchemy 操作错误
- `sqlalchemy.exc.InterfaceError` - SQLAlchemy 接口错误
- `sqlalchemy.exc.DatabaseError` - SQLAlchemy 数据库错误
- `sqlalchemy.exc.DisconnectionError` - 连接断开错误

### 3. 非重试异常

以下异常类型**不会**触发重试，会直接抛出：

- 语法错误
- 约束错误（如主键冲突）
- 权限错误
- 其他业务逻辑异常

## 已集成的操作方法

以下数据库操作方法都已集成重试机制：

### 1. 查询操作

```python
db = get_database()

# 自动重试的查询
result = db.execute_query("SELECT * FROM stocks WHERE code = ?", ('000001',))
```

### 2. 更新操作

```python
# 自动重试的更新
affected = db.execute_update(
    "UPDATE stocks SET name = ? WHERE code = ?", 
    ('平安银行', '000001')
)
```

### 3. 批量操作

```python
# 自动重试的批量插入
data = [
    ('000001', '平安银行'),
    ('000002', '万科A'),
]
affected = db.execute_many(
    "INSERT INTO stocks (code, name) VALUES (?, ?)",
    data
)
```

### 4. ORM 操作

```python
# 自动重试的 ORM 插入
db.insert_one('stocks', {
    'code': '000001',
    'name': '平安银行'
})

# 自动重试的 ORM 更新
db.update_one('stocks', 
    {'name': '平安银行'},
    {'code': '000001'}
)

# 自动重试的 ORM 删除
db.delete('stocks', {'code': '000001'})
```

## 重试行为示例

### 正常情况（不触发重试）

```python
# 连接正常，查询立即成功
result = db.execute_query("SELECT 1 as test")
# 耗时: 0.001s
# 日志: 无重试日志
```

### 异常情况（触发重试）

```python
# 第一次失败，自动重试
result = db.execute_query("SELECT * FROM large_table")

# 重试行为:
# 第1次尝试: 失败 (OperationalError: Lost connection)
# 等待: 0.5秒
# 第2次尝试: 失败 (OperationalError: Lost connection)
# 等待: 1秒
# 第3次尝试: 失败 (OperationalError: Lost connection)
# 等待: 2秒
# 第4次尝试: 成功
# 总耗时: 约 3.5秒（含重试延迟）
```

### 超过最大重试次数

```python
# 所有重试都失败
result = db.execute_query("SELECT * FROM table")

# 重试行为:
# 第1次尝试: 失败
# 第2次尝试: 失败
# 第3次尝试: 失败
# 第4次尝试: 失败
# 抛出异常: sqlalchemy.exc.OperationalError
# 日志: ERROR - 数据库操作失败，已达到最大重试次数 3
```

## 配置重试参数

### 修改默认重试参数

编辑 [app/utils/db_retry.py](app/utils/db_retry.py)，修改装饰器的默认参数：

```python
# 默认配置
@retry_db_operation(
    max_retries=3,        # 最大重试次数
    retry_delay=0.5,      # 初始重试延迟（秒）
    backoff_factor=2.0,   # 退避因子
    retry_exceptions=None  # 默认重试所有数据库异常
)
```

### 自定义重试参数

如果需要为特定方法自定义重试参数，可以在方法内部修改：

```python
from app.utils.db_retry import retry_db_operation

@retry_db_operation(max_retries=5, retry_delay=1.0)
def custom_query():
    # 自定义重试：最多5次，初始延迟1秒
    pass
```

### 自定义重试异常类型

```python
from pymysql import OperationalError
from sqlalchemy.exc import DisconnectionError

@retry_db_operation(
    max_retries=3,
    retry_exceptions=(OperationalError, DisconnectionError)
)
def specific_retry():
    # 只对指定的异常类型重试
    pass
```

## 测试重试机制

运行测试脚本验证重试机制：

```bash
source venv/bin/activate
python test_db_retry.py
```

测试内容包括：
1. 正常查询（验证不需要重试）
2. 连接稳定性测试
3. 并发查询测试
4. 更新操作测试
5. 批量插入测试

## 日志监控

### 重试日志示例

```log
2025-12-29 15:28:57,123 - app.utils.db_retry - WARNING - 数据库操作失败，准备第 1/3 次重试，函数: _execute，异常: OperationalError: Lost connection to MySQL server during query，等待 0.50 秒后重试...

2025-12-29 15:28:57,624 - app.utils.db_retry - WARNING - 数据库操作失败，准备第 2/3 次重试，函数: _execute，异常: OperationalError: Lost connection to MySQL server during query，等待 1.00 秒后重试...

2025-12-29 15:28:58,625 - app.utils.db_retry - ERROR - 数据库操作失败，已达到最大重试次数 3，函数: _execute，异常: OperationalError: Lost connection to MySQL server during query
```

### 日志级别说明

- **WARNING**: 触发重试，但仍在尝试中
- **ERROR**: 已达到最大重试次数，放弃重试

## 最佳实践

### 1. 合理设置重试次数

根据业务场景调整重试次数：

```python
# 关键业务操作：增加重试次数
@retry_db_operation(max_retries=5, retry_delay=0.5)
def critical_operation():
    pass

# 非关键操作：减少重试次数
@retry_db_operation(max_retries=1, retry_delay=0.3)
def non_critical_operation():
    pass
```

### 2. 避免长时间运行的事务

重试机制不适合长时间运行的事务，因为重试会重复执行整个操作：

```python
# 不推荐：长时间事务
@retry_db_operation()
def long_transaction():
    db.execute_update("INSERT INTO table1 ...")
    time.sleep(60)  # 长时间等待
    db.execute_update("INSERT INTO table2 ...")
```

### 3. 幂等性考虑

确保操作是幂等的，重试不会产生副作用：

```python
# 推荐：使用 ON DUPLICATE KEY UPDATE
db.execute_update("""
    INSERT INTO stocks (code, name) 
    VALUES (?, ?)
    ON DUPLICATE KEY UPDATE name = VALUES(name)
""", ('000001', '平安银行'))
```

### 4. 监控重试频率

定期检查日志，监控重试频率：

```bash
# 统计重试次数
grep "准备第.*次重试" logs/app.log | wc -l

# 查看最近的重试日志
grep "重试" logs/app.log | tail -20
```

### 5. 配合连接池优化

重试机制与连接池配合使用效果最佳：

```yaml
# config.yaml
database:
  mysql:
    pool:
      size: 10
      max_overflow: 20
      timeout: 60
      recycle: 1800
```

## 性能影响

### 正常情况（无重试）

- **性能开销**: 几乎无开销（装饰器只增加一次函数调用）
- **延迟**: 不增加延迟

### 异常情况（触发重试）

- **第1次重试**: +0.5 秒延迟
- **第2次重试**: +1.0 秒延迟（累计 1.5 秒）
- **第3次重试**: +2.0 秒延迟（累计 3.5 秒）

### 并发场景

- 多个线程同时重试不会相互影响
- 每个线程独立进行重试

## 故障排查

### 重试一直失败

如果重试一直失败，检查：

1. **数据库连接配置**
   ```python
   # 检查连接字符串
   logger.info(f"数据库URL: {db.orm_db.db_url}")
   ```

2. **网络连接**
   ```bash
   telnet localhost 3306
   ```

3. **数据库服务器状态**
   ```sql
   SHOW STATUS LIKE 'Threads_connected';
   SHOW VARIABLES LIKE 'max_connections';
   ```

4. **连接池状态**
   ```bash
   python diagnose_database_pool.py
   ```

### 重试次数过多

如果重试次数过多，说明系统不稳定，需要：

1. **检查数据库服务器负载**
2. **优化查询语句**
3. **增加连接池大小**
4. **检查网络延迟**

### 非预期异常不重试

如果某些异常应该重试但未被重试：

1. **检查异常类型**
   ```python
   import traceback
   traceback.print_exc()  # 查看异常类型
   ```

2. **添加到重试异常列表**
   ```python
   retry_exceptions=(OperationalError, YourCustomException)
   ```

## 技术实现

### 重试装饰器实现

位置: [app/utils/db_retry.py](app/utils/db_retry.py)

```python
def retry_db_operation(
    max_retries: int = 3,
    retry_delay: float = 0.5,
    backoff_factor: float = 2.0,
    retry_exceptions: Tuple[Type[Exception], ...] = None
):
    """数据库操作重试装饰器"""
    # 实现细节...
```

### 集成方式

所有数据库操作方法都通过内部函数调用装饰器：

```python
def execute_query(self, query: str, params: tuple = None) -> list:
    @retry_db_operation(max_retries=3, retry_delay=0.5)
    def _execute():
        # 实际的数据库操作
        pass
    
    return _execute()
```

## 总结

✓ **重试机制已自动集成**到所有 ORM 数据库操作方法
✓ **默认配置**：最多重试 3 次，初始延迟 0.5 秒，指数退避
✓ **支持异常**：OperationalError, InterfaceError, DatabaseError 等
✓ **智能过滤**：只对数据库相关异常重试，业务异常直接抛出
✓ **性能优化**：正常情况无开销，异常情况自动恢复
✓ **易于监控**：详细的日志记录重试行为

通过重试机制，系统在面对瞬时的数据库连接问题时，可以自动恢复，提高系统的稳定性和可靠性，无需人工干预。
