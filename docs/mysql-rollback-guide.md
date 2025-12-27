# MySQL 迁移回滚指南

## 目录

- [概述](#概述)
- [回滚场景](#回滚场景)
- [回滚流程](#回滚流程)
- [手动回滚](#手动回滚)
- [恢复备份](#恢复备份)
- [验证回滚](#验证回滚)
- [故障排查](#故障排查)

---

## 概述

本文档提供了将股票分析系统从 MySQL 回滚到 SQLite 数据库的完整指南。

### 回滚注意事项

⚠️ **重要提示**:
- 回滚前务必备份当前 MySQL 数据
- 回滚操作会停止使用 MySQL，恢复到 SQLite
- 回滚期间系统可能需要短暂停机
- 建议在低峰期执行回滚操作

### 回滚工具

项目提供了自动回滚工具：
```bash
python tools/rollback_migration.py
```

---

## 回滚场景

### 场景 1: 迁移失败

迁移过程中出现错误，需要回滚到 SQLite。

### 场景 2: 性能问题

MySQL 性能不如预期，需要回滚到 SQLite。

### 场景 3: 兼容性问题

应用在 MySQL 下出现兼容性问题，需要回滚。

### 场景 4: 运维需要

运维原因需要临时切换回 SQLite。

---

## 回滚流程

### 自动回滚（推荐）

使用项目提供的回滚工具：

```bash
# 基本回滚
python tools/rollback_migration.py

# 回滚并清空 MySQL 数据
python tools/rollback_migration.py --clear-mysql

# 仅生成恢复指南（不执行实际回滚）
python tools/rollback_migration.py --guide-only
```

#### 回滚工具功能

回滚工具会自动完成以下步骤：

1. **备份 SQLite 数据库**
   - 备份当前的 SQLite 数据库文件
   - 保存到备份目录

2. **备份配置文件**
   - 备份当前配置文件
   - 保存到备份目录

3. **测试 SQLite 数据库**
   - 验证 SQLite 数据库是否可用
   - 确认数据完整性

4. **恢复配置为 SQLite**
   - 修改配置文件中的数据库类型
   - 保存配置

5. **清空 MySQL 数据（可选）**
   - 删除 MySQL 中的所有数据
   - 需要用户确认

6. **生成恢复指南**
   - 生成手动恢复步骤文档
   - 保存到备份目录

---

## 手动回滚

如果自动回滚工具不可用，可以按照以下步骤手动回滚。

### 步骤 1: 备份当前数据

#### 备份 SQLite 数据库

```bash
# 创建备份目录
mkdir -p ./data/backups

# 备份 SQLite 数据库
cp ./data/stock_analysis.db ./data/backups/stock_analysis_rollback_$(date +%Y%m%d_%H%M%S).db
```

#### 备份配置文件

```bash
cp ./config.yaml ./data/backups/config_rollback_$(date +%Y%m%d_%H%M%S).yaml
```

#### 备份 MySQL 数据（可选）

```bash
# 使用 mysqldump 备份 MySQL 数据
mysqldump -u username -p database_name > ./data/backups/mysql_backup_$(date +%Y%m%d_%H%M%S).sql
```

### 步骤 2: 验证 SQLite 数据库

```bash
# 检查 SQLite 数据库文件是否存在
ls -lh ./data/stock_analysis.db

# 使用 sqlite3 检查数据库
sqlite3 ./data/stock_analysis.db "SELECT COUNT(*) FROM stocks;"
sqlite3 ./data/stock_analysis.db ".schema"
```

### 步骤 3: 修改配置文件

编辑 `config.yaml` 文件：

```yaml
database:
  type: sqlite  # 改为 sqlite
  sqlite_path: ./data/stock_analysis.db
  duckdb_path: ./data/market_data.duckdb
```

### 步骤 4: 停止应用

```bash
# 根据实际部署方式停止应用
# 例如：
pkill -f "python main.py"
# 或
systemctl stop stock-analysis-app
```

### 步骤 5: 重启应用

```bash
# 启动应用
python main.py

# 或使用系统服务
systemctl start stock-analysis-app
```

### 步骤 6: 验证系统运行

```bash
# 检查应用日志
tail -f ./logs/app.log

# 访问应用界面，确认功能正常
```

### 步骤 7: 清空 MySQL 数据（可选）

如果确定不再需要 MySQL 数据，可以清空：

```bash
# 使用 MySQL 客户端连接
mysql -u username -p database_name

# 执行清空命令
DELETE FROM stocks;
DELETE FROM strategies;
DELETE FROM strategy_results;
DELETE FROM system_logs;
DELETE FROM data_update_history;
DELETE FROM job_logs;
DELETE FROM task_execution_details;

# 退出
exit
```

---

## 恢复备份

### 恢复 SQLite 数据库

如果 SQLite 数据库损坏，可以从备份恢复：

```bash
# 停止应用
pkill -f "python main.py"

# 从备份恢复
cp ./data/backups/stock_analysis_backup_YYYYMMDD_HHMMSS.db ./data/stock_analysis.db

# 重启应用
python main.py
```

### 恢复配置文件

```bash
# 从备份恢复配置
cp ./data/backups/config_backup_YYYYMMDD_HHMMSS.yaml ./config.yaml

# 重启应用
python main.py
```

### 恢复 MySQL 数据

如果需要恢复 MySQL 数据：

```bash
# 使用 mysql 客户端恢复
mysql -u username -p database_name < ./data/backups/mysql_backup_YYYYMMDD_HHMMSS.sql
```

---

## 验证回滚

### 验证项目

1. **应用启动**
   - 确认应用可以正常启动
   - 检查日志无错误信息

2. **数据完整性**
   - 确认股票列表可以正常显示
   - 确认策略配置可以正常查看
   - 确认历史数据可以正常访问

3. **功能验证**
   - 测试数据查询功能
   - 测试策略执行功能
   - 测试日志记录功能

### 验证命令

```sql
-- 检查 SQLite 数据库
sqlite3 ./data/stock_analysis.db "SELECT COUNT(*) FROM stocks;"
sqlite3 ./data/stock_analysis.db "SELECT COUNT(*) FROM strategies;"
```

---

## 故障排查

### 问题 1: 应用启动失败

**错误信息**: `No such file or directory: ./data/stock_analysis.db`

**解决方案**:
- 检查 SQLite 数据库文件是否存在
- 检查配置文件中的路径是否正确
- 从备份恢复数据库文件

### 问题 2: 数据加载异常

**错误信息**: `Database is locked`

**解决方案**:
- 确认应用已完全停止
- 检查是否有其他进程在使用数据库
- 重启系统后再试

### 问题 3: 配置文件格式错误

**错误信息**: `YAML syntax error`

**解决方案**:
- 使用 YAML 验证工具检查配置文件
- 从备份恢复配置文件
- 检查缩进和语法

### 问题 4: 权限问题

**错误信息**: `Permission denied`

**解决方案**:
- 检查文件和目录权限
- 使用正确的用户运行应用
- 修改权限：`chmod 644 ./data/stock_analysis.db`

### 问题 5: 数据不一致

**错误信息**: 数据缺失或数据不匹配

**解决方案**:
- 使用数据验证工具检查数据
- 从备份恢复完整的数据
- 重新执行迁移流程

---

## 常见问题

### Q1: 回滚后 MySQL 数据会被删除吗？

**A**: 默认不会删除 MySQL 数据。如果需要删除，使用 `--clear-mysql` 参数或手动清空。

### Q2: 回滚会影响应用的运行吗？

**A**: 回滚期间需要停止应用，回滚完成后重启应用即可正常运行。

### Q3: 可以从 MySQL 再次迁移到 SQLite 吗？

**A**: 可以，但需要开发专门的 MySQL 到 SQLite 迁移工具。

### Q4: 回滚后可以再次迁移到 MySQL 吗？

**A**: 可以，使用迁移工具重新执行迁移即可。

### Q5: 备份数据保留多久？

**A**: 建议保留至少 30 天，根据实际情况调整备份保留策略。

---

## 最佳实践

### 1. 定期备份

建议每天自动备份：
```bash
# 添加到 crontab
0 2 * * * /path/to/backup_script.sh
```

### 2. 回滚测试

在生产环境回滚前，先在测试环境进行测试。

### 3. 监控和日志

- 详细记录回滚过程中的每一步
- 监控系统运行状态
- 保留完整的日志信息

### 4. 快速恢复

准备快速恢复脚本，减少停机时间。

### 5. 文档更新

回滚完成后，更新相关文档和配置。

---

## 附录

### A. 备份目录结构

```
data/backups/
├── stock_analysis_backup_20251227_140000.db
├── config_backup_20251227_140000.yaml
├── mysql_backup_20251227_140000.sql
└── manual_recovery_guide_20251227_140000.md
```

### B. 回滚检查清单

在执行回滚前，请确认：

- [ ] 已备份 SQLite 数据库
- [ ] 已备份配置文件
- [ ] 已验证 SQLite 数据库可用
- [ ] 已通知相关人员
- [ ] 已选择合适的执行时间
- [ ] 已准备回滚工具
- [ ] 已准备好应急预案

### C. 联系支持

如遇到无法解决的问题：

1. 查看应用日志
2. 查看本文档的故障排查部分
3. 联系技术支持

---

## 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.0 | 2025-12-27 | 初始版本 |
