# MySQL 备份和恢复工具使用说明

## 概述

`mysql_backup_restore.py` 是一个用于 MySQL 数据库备份和恢复的工具，它从 `config.yaml` 文件中读取 MySQL 的连接配置，提供便捷的数据库备份和恢复功能。

## 功能特性

### 备份功能
- ✅ 备份整个数据库
- ✅ 备份指定表
- ✅ 自动压缩备份文件（gzip）
- ✅ 自动生成备份文件名（带时间戳）
- ✅ 支持自定义输出路径
- ✅ 包含存储过程、函数、触发器和事件

### 恢复功能
- ✅ 从备份文件恢复数据库
- ✅ 支持压缩文件（.sql.gz）
- ✅ 可选择删除并重建数据库
- ✅ 支持恢复指定表

### 管理功能
- ✅ 列出所有备份文件
- ✅ 列出数据库中的表
- ✅ 清理旧备份
- ✅ 显示备份文件大小和修改时间

## 依赖要求

确保系统已安装以下工具：
- `mysqldump` - MySQL 备份工具
- `mysql` - MySQL 客户端
- Python 3.x
- PyYAML 库

安装 PyYAML：
```bash
pip install pyyaml
```

## 配置文件

工具会自动从 `config.yaml` 读取 MySQL 配置：

```yaml
database:
  type: mysql
  mysql:
    host: localhost
    port: 3306
    database: stock_analysis
    username: stock_user
    password: your_password
    charset: utf8mb4
```

备份目录默认为 `./data/backups/mysql`，也可在配置中指定：
```yaml
data_management:
  backup_dir: ./data/backups
```

## 使用方法

### 1. 备份整个数据库

```bash
# 基本用法
python tools/mysql_backup_restore.py backup

# 使用绝对路径
cd /data/home/aaronpan/stock-analysis-app
python tools/mysql_backup_restore.py backup
```

**输出示例**：
```
2023-12-28 14:30:00 - INFO - MySQL 配置加载成功: localhost:3306
2023-12-28 14:30:00 - INFO - 备份数据库: stock_analysis
2023-12-28 14:30:00 - INFO - 备份目录: ./data/backups/mysql
2023-12-28 14:30:00 - INFO - 开始备份: stock_analysis
2023-12-28 14:30:00 - INFO - 输出文件: ./data/backups/mysql/stock_analysis_20231228_143000.sql.gz
2023-12-28 14:30:05 - INFO - 备份成功: ./data/backups/mysql/stock_analysis_20231228_143000.sql.gz
2023-12-28 14:30:05 - INFO - 文件大小: 2.34 MB

✓ 备份成功: ./data/backups/mysql/stock_analysis_20231228_143000.sql.gz
```

### 1.1 使用命令行参数指定数据库凭据

```bash
# 使用自定义用户名（密码从配置文件读取）
python tools/mysql_backup_restore.py backup --username admin

# 使用交互式密码输入（用户名从配置文件读取）
python tools/mysql_backup_restore.py backup -p
# 会提示: 请输入数据库密码:

# 同时指定用户名和交互式密码
python tools/mysql_backup_restore.py backup --username admin -p
# 会提示: 请输入数据库密码:

# 使用自定义用户名和密码进行恢复
python tools/mysql_backup_restore.py restore --backup backup.sql.gz -u root -p
```

### 2. 备份指定表

```bash
# 备份单个表
python tools/mysql_backup_restore.py backup --tables users

# 备份多个表
python tools/mysql_backup_restore.py backup --tables users stocks strategies
```

**输出示例**：
```
2023-12-28 14:31:00 - INFO - 开始备份: stock_analysis
2023-12-28 14:31:00 - INFO - 备份表: users, stocks, strategies
2023-12-28 14:31:03 - INFO - 备份成功: ./data/backups/mysql/stock_analysis_users_stocks_strategies_20231228_143100.sql.gz
```

### 3. 备份到指定文件

```bash
# 自定义输出路径
python tools/mysql_backup_restore.py backup --output /path/to/custom_backup.sql.gz

# 不压缩
python tools/mysql_backup_restore.py backup --output /path/to/custom_backup.sql --no-compress
```

### 4. 列出所有备份

```bash
python tools/mysql_backup_restore.py list
```

**输出示例**：
```
====================================================================================================
文件名                                              大小          修改时间
====================================================================================================
stock_analysis_20231228_143000.sql.gz                2.34 MB      2023-12-28 14:30:00
stock_analysis_20231227_120000.sql.gz                2.30 MB      2023-12-27 12:00:00
stock_analysis_users_20231226_180000.sql.gz          156 KB       2023-12-26 18:00:00
====================================================================================================
总计: 3 个备份文件
```

### 5. 列出数据库中的表

```bash
python tools/mysql_backup_restore.py tables
```

**输出示例**：
```
数据库中的表 (5 个):
  - users
  - stocks
  - strategies
  - tasks
  - task_results
```

### 6. 恢复数据库

```bash
# 恢复到现有数据库
python tools/mysql_backup_restore.py restore --backup ./data/backups/mysql/stock_analysis_20231228_143000.sql.gz

# 恢复并重建数据库（会先删除现有数据库）
python tools/mysql_backup_restore.py restore --backup ./data/backups/mysql/stock_analysis_20231228_143000.sql.gz --drop --create
```

**输出示例**：
```
2023-12-28 14:35:00 - INFO - MySQL 配置加载成功: localhost:3306
2023-12-28 14:35:00 - INFO - 备份数据库: stock_analysis
2023-12-28 14:35:00 - INFO - 备份目录: ./data/backups/mysql
2023-12-28 14:35:00 - INFO - 开始恢复: ./data/backups/mysql/stock_analysis_20231228_143000.sql.gz
2023-12-28 14:35:00 - INFO - 目标数据库: stock_analysis
2023-12-28 14:35:05 - INFO - 恢复成功: ./data/backups/mysql/stock_analysis_20231228_143000.sql.gz

✓ 恢复成功
```

### 7. 清理旧备份

```bash
# 保留最近 5 个备份
python tools/mysql_backup_restore.py cleanup

# 保留最近 3 个备份
python tools/mysql_backup_restore.py cleanup --keep 3
```

## 命令参考

### 全局参数
- `--config, -c`: 配置文件路径（默认: config.yaml）
- `--username, -u`: 数据库用户名（覆盖配置文件中的设置）
- `--password, -p`: 交互式输入数据库密码（覆盖配置文件中的设置）

### backup 命令
- `--database, -d`: 数据库名称（默认使用配置文件中的数据库）
- `--tables, -t`: 要备份的表名列表（空格分隔）
- `--output, -o`: 输出文件路径（默认自动生成）
- `--no-compress`: 不压缩备份文件

### restore 命令
- `--backup, -b`: 备份文件路径（必需）
- `--database, -d`: 数据库名称（默认使用配置文件中的数据库）
- `--drop`: 恢复前删除数据库
- `--create`: 创建数据库
- `--tables, -t`: 只恢复这些表

### list 命令
无参数，列出所有备份文件

### tables 命令
- `--database, -d`: 数据库名称

### cleanup 命令
- `--keep, -k`: 保留的备份数量（默认: 5）

## 使用场景示例

### 场景 1：用户管理功能开发前备份

```bash
# 1. 创建完整备份
python tools/mysql_backup_restore.py backup

# 2. 记录备份文件名
# 输出: ./data/backups/mysql/stock_analysis_20231228_143000.sql.gz

# 3. 开始开发用户管理功能
```

### 场景 2：只备份用户相关表

```bash
# 只备份用户相关的表
python tools/mysql_backup_restore.py backup --tables users user_roles user_permissions
```

### 场景 3：恢复到开发前的状态

```bash
# 1. 查看可用备份
python tools/mysql_backup_restore.py list

# 2. 恢复指定备份
python tools/mysql_backup_restore.py restore \
  --backup ./data/backups/mysql/stock_analysis_20231228_143000.sql.gz \
  --drop --create
```

### 场景 4：定期备份脚本

创建定期备份脚本 `scripts/daily_backup.sh`：

```bash
#!/bin/bash
# 每日数据库备份脚本

cd /data/home/aaronpan/stock-analysis-app

# 备份数据库
python tools/mysql_backup_restore.py backup

# 清理 7 天前的备份
python tools/mysql_backup_restore.py cleanup --keep 7
```

添加到 crontab：
```bash
# 每天凌晨 2 点执行备份
0 2 * * * /data/home/aaronpan/stock-analysis-app/scripts/daily_backup.sh >> /var/log/stock_backup.log 2>&1
```

## 注意事项

### 安全性
1. **密码安全**：`mysqldump` 会将密码包含在命令行中，进程列表可能可见
2. **备份文件**：备份文件包含完整数据，应妥善保管
3. **文件权限**：确保备份目录只有授权用户可访问

### 最佳实践
1. **定期测试**：定期测试备份文件的完整性
2. **异地备份**：将重要备份复制到远程存储
3. **备份前停止写操作**：生产环境建议在维护窗口期备份
4. **验证恢复**：在测试环境验证恢复流程

### 性能优化
1. **大数据库**：对于大数据库，建议在非高峰期备份
2. **网络延迟**：如果是远程数据库，注意网络延迟
3. **磁盘空间**：确保有足够的磁盘空间存储备份

## 故障排查

### 问题：找不到 mysqldump 命令

**解决方案**：
```bash
# 检查 mysqldump 是否安装
which mysqldump

# Ubuntu/Debian 安装
sudo apt-get install mysql-client

# CentOS/RHEL 安装
sudo yum install mysql-client
```

### 问题：权限不足

**解决方案**：
```bash
# 确保 MySQL 用户有足够的权限
GRANT SELECT, LOCK TABLES, SHOW VIEW, EVENT, TRIGGER ON stock_analysis.* TO 'stock_user'@'%';
FLUSH PRIVILEGES;
```

### 问题：恢复失败

**解决方案**：
1. 检查备份文件完整性
2. 确保目标数据库已创建或使用 `--create` 参数
3. 检查磁盘空间
4. 查看错误日志

### 问题：备份文件太大

**解决方案**：
```bash
# 1. 只备份需要的表
python tools/mysql_backup_restore.py backup --tables users stocks

# 2. 不压缩备份（便于分块传输）
python tools/mysql_backup_restore.py backup --no-compress

# 3. 使用其他压缩工具
gzip -9 backup.sql
```

## 高级用法

### 1. 使用自定义配置文件

```bash
python tools/mysql_backup_restore.py --config /path/to/custom_config.yaml backup
```

### 2. 使用命令行参数覆盖配置文件

```bash
# 临时使用不同的数据库用户
python tools/mysql_backup_restore.py backup --username dbadmin -p

# 在恢复时使用管理员账户
python tools/mysql_backup_restore.py restore --backup backup.sql.gz --drop --create -u root -p
```

### 3. 备份到远程服务器

```bash
# 备份并上传到远程服务器
python tools/mysql_backup_restore.py backup --output /tmp/backup.sql.gz
scp /tmp/backup.sql.gz user@remote-server:/path/to/backups/
```

### 3. 恢复到不同的数据库

```bash
# 备份源数据库
python tools/mysql_backup_restore.py backup --output source_backup.sql.gz

# 恢复到目标数据库（修改配置中的数据库名或使用 --database 参数）
python tools/mysql_backup_restore.py restore \
  --backup source_backup.sql.gz \
  --database target_database \
  --create
```

### 4. 自动化脚本示例

```python
# automated_backup.py
import os
import sys
from tools.mysql_backup_restore import MySQLBackupRestore

def automated_backup():
    """自动化备份脚本"""
    try:
        tool = MySQLBackupRestore()
        
        # 备份整个数据库
        backup_file = tool.backup()
        print(f"备份成功: {backup_file}")
        
        # 清理旧备份，保留最近 10 个
        tool.cleanup_old_backups(keep_count=10)
        
        # 可选：上传到远程服务器
        # os.system(f"scp {backup_file} remote:/backups/")
        
        return backup_file
        
    except Exception as e:
        print(f"备份失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    automated_backup()
```

## 获取帮助

```bash
# 查看帮助信息
python tools/mysql_backup_restore.py --help

# 查看特定命令的帮助
python tools/mysql_backup_restore.py backup --help
python tools/mysql_backup_restore.py restore --help
```

## 总结

这个工具提供了完整的 MySQL 数据库备份和恢复功能，适合在开发、测试和生产环境中使用。建议在重要操作前创建备份，并定期测试备份和恢复流程。

---

**最后更新**: 2023-12-28  
**版本**: 1.0
