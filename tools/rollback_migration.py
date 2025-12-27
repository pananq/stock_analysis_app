#!/usr/bin/env python3
"""
迁移回滚工具
用于将系统从MySQL回滚到SQLite，包括配置恢复和数据清理
"""
import sys
import shutil
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.utils import get_logger
from app.models.sqlite_db import SQLiteDB
from app.models.mysql_db import MySQLDB
from app.utils.config import get_config
from app.models.database_factory import switch_database, get_database

logger = get_logger(__name__)


class MigrationRollback:
    """迁移回滚工具类"""
    
    # 需要清理的表
    TABLES_TO_CLEAR = [
        'stocks',
        'strategies',
        'strategy_results',
        'system_logs',
        'data_update_history',
        'job_logs',
        'task_execution_details'
    ]
    
    def __init__(self):
        """初始化回滚工具"""
        self.config = None
        self.backup_dir = None
        self.sqlite_db = None
        self.mysql_db = None
    
    def setup_backup_directory(self) -> Path:
        """
        创建备份目录
        
        Returns:
            备份目录路径
        """
        config = get_config()
        backup_path = config.get('data_management.backup_dir', './data/backups')
        self.backup_dir = Path(backup_path)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        return self.backup_dir
    
    def backup_sqlite_database(self, sqlite_path: str) -> Path:
        """
        备份SQLite数据库文件
        
        Args:
            sqlite_path: SQLite数据库文件路径
            
        Returns:
            备份文件路径
        """
        self.setup_backup_directory()
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        sqlite_file = Path(sqlite_path)
        backup_file = self.backup_dir / f"{sqlite_file.stem}_backup_{timestamp}{sqlite_file.suffix}"
        
        if sqlite_file.exists():
            shutil.copy2(sqlite_path, backup_file)
            logger.info(f"SQLite数据库已备份到: {backup_file}")
            print(f"✓ SQLite数据库已备份到: {backup_file}")
            return backup_file
        else:
            logger.warning(f"SQLite数据库文件不存在: {sqlite_path}")
            return None
    
    def backup_config_file(self) -> Path:
        """
        备份配置文件
        
        Returns:
            备份文件路径
        """
        self.setup_backup_directory()
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        config_path = project_root / 'config.yaml'
        backup_file = self.backup_dir / f"config_backup_{timestamp}.yaml"
        
        if config_path.exists():
            shutil.copy2(config_path, backup_file)
            logger.info(f"配置文件已备份到: {backup_file}")
            print(f"✓ 配置文件已备份到: {backup_file}")
            return backup_file
        else:
            logger.warning(f"配置文件不存在: {config_path}")
            return None
    
    def clear_mysql_tables(self, mysql_config: Dict[str, Any]) -> bool:
        """
        清空MySQL中的所有数据
        
        Args:
            mysql_config: MySQL配置字典
            
        Returns:
            是否成功
        """
        print("\n警告: 即将清空MySQL数据库中的所有数据！")
        print("受影响的表:", ', '.join(self.TABLES_TO_CLEAR))
        
        confirm = input("确认要清空吗？(yes/no): ")
        if confirm.lower() not in ['yes', 'y']:
            print("取消清空操作")
            return False
        
        try:
            self.mysql_db = MySQLDB(mysql_config)
            logger.info("开始清空MySQL数据...")
            
            for table in self.TABLES_TO_CLEAR:
                query = f"DELETE FROM {table}"
                affected_rows = self.mysql_db.execute_update(query)
                logger.info(f"表 {table}: 已清空 {affected_rows} 条记录")
                print(f"✓ 表 {table}: 已清空 {affected_rows} 条记录")
            
            logger.info("MySQL数据清空完成")
            return True
            
        except Exception as e:
            logger.error(f"清空MySQL数据失败: {e}", exc_info=True)
            print(f"✗ 清空MySQL数据失败: {e}")
            return False
        finally:
            if self.mysql_db:
                self.mysql_db.close_all_connections()
    
    def restore_config_to_sqlite(self) -> bool:
        """
        将配置文件中的数据库类型恢复为SQLite
        
        Returns:
            是否成功
        """
        try:
            config = get_config()
            
            # 检查当前数据库类型
            current_type = config.get('database.type', 'sqlite')
            if current_type == 'sqlite':
                print("当前数据库类型已经是SQLite，无需恢复")
                return True
            
            # 备份当前配置
            self.backup_config_file()
            
            # 恢复为SQLite
            config.set('database.type', 'sqlite')
            config.save()
            
            logger.info("配置已恢复为SQLite")
            print(f"✓ 配置已恢复为SQLite")
            
            return True
            
        except Exception as e:
            logger.error(f"恢复配置失败: {e}", exc_info=True)
            print(f"✗ 恢复配置失败: {e}")
            return False
    
    def test_sqlite_database(self, sqlite_path: str) -> bool:
        """
        测试SQLite数据库是否可以正常使用
        
        Args:
            sqlite_path: SQLite数据库文件路径
            
        Returns:
            是否可用
        """
        try:
            self.sqlite_db = SQLiteDB(sqlite_path)
            
            # 测试查询
            query = "SELECT COUNT(*) as count FROM stocks"
            result = self.sqlite_db.execute_query(query)
            
            logger.info(f"SQLite数据库测试通过，stocks表记录数: {result[0]['count']}")
            print(f"✓ SQLite数据库测试通过")
            
            return True
            
        except Exception as e:
            logger.error(f"SQLite数据库测试失败: {e}", exc_info=True)
            print(f"✗ SQLite数据库测试失败: {e}")
            return False
    
    def rollback(self, clear_mysql: bool = False) -> bool:
        """
        执行完整的回滚流程
        
        Args:
            clear_mysql: 是否清空MySQL数据
            
        Returns:
            是否成功
        """
        print("=" * 60)
        print("MySQL到SQLite回滚工具")
        print("=" * 60)
        
        try:
            # 获取配置
            config = get_config()
            
            # 获取SQLite路径
            sqlite_path = config.get('database.sqlite_path')
            if not sqlite_path:
                print("错误: 未配置SQLite数据库路径")
                return False
            
            # 获取MySQL配置
            mysql_config = config.get('database.mysql')
            if not mysql_config:
                print("错误: 未配置MySQL数据库参数")
                return False
            
            print(f"\n当前配置:")
            print(f"  SQLite路径: {sqlite_path}")
            print(f"  MySQL配置: {mysql_config['host']}:{mysql_config['port']}/{mysql_config['database']}")
            
            # 步骤1: 备份SQLite数据库
            print("\n[步骤 1/4] 备份SQLite数据库...")
            sqlite_backup = self.backup_sqlite_database(sqlite_path)
            if not sqlite_backup:
                print("警告: SQLite数据库备份失败或文件不存在")
            
            # 步骤2: 测试SQLite数据库
            print("\n[步骤 2/4] 测试SQLite数据库可用性...")
            sqlite_ok = self.test_sqlite_database(sqlite_path)
            if not sqlite_ok:
                print("错误: SQLite数据库不可用，无法回滚")
                return False
            
            # 步骤3: 恢复配置为SQLite
            print("\n[步骤 3/4] 恢复配置为SQLite...")
            config_ok = self.restore_config_to_sqlite()
            if not config_ok:
                print("错误: 配置恢复失败")
                return False
            
            # 步骤4: 可选：清空MySQL数据
            if clear_mysql:
                print("\n[步骤 4/4] 清空MySQL数据...")
                mysql_ok = self.clear_mysql_tables(mysql_config)
                if not mysql_ok:
                    print("警告: MySQL数据清空失败")
            
            print("\n" + "=" * 60)
            print("回滚完成")
            print("=" * 60)
            print("\n系统已回滚到SQLite数据库")
            print("请重启应用以使配置生效")
            
            return True
            
        except Exception as e:
            logger.error(f"回滚失败: {e}", exc_info=True)
            print(f"\n✗ 回滚失败: {e}")
            return False
    
    def generate_manual_recovery_guide(self) -> Path:
        """
        生成手动恢复步骤文档
        
        Returns:
            文档文件路径
        """
        self.setup_backup_directory()
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        guide_file = self.backup_dir / f"manual_recovery_guide_{timestamp}.md"
        
        config = get_config()
        sqlite_path = config.get('database.sqlite_path')
        
        content = f"""# 手动恢复步骤指南

生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 前提条件

1. SQLite数据库文件位于: `{sqlite_path}`
2. 备份目录: `{self.backup_dir}`
3. MySQL数据库配置已准备

## 恢复步骤

### 1. 验证SQLite数据库

```bash
# 检查SQLite数据库文件是否存在
ls -lh {sqlite_path}

# 使用sqlite3检查数据库
sqlite3 {sqlite_path} "SELECT COUNT(*) FROM stocks;"
```

### 2. 修改配置文件

编辑 `{project_root}/config.yaml`:

```yaml
database:
  type: sqlite  # 改为 sqlite
  sqlite_path: ./data/stock_analysis.db
```

### 3. 重启应用

```bash
# 停止应用
# 根据实际部署方式执行

# 启动应用
python main.py
```

### 4. 验证系统运行

访问应用界面，确认:
- 股票列表可以正常显示
- 策略配置可以正常查看
- 系统日志可以正常记录

## 清理MySQL数据（可选）

如果需要清空MySQL中的数据:

```bash
# 使用MySQL客户端连接
mysql -h <host> -P <port> -u <username> -p <database>

# 执行清空命令
DELETE FROM stocks;
DELETE FROM strategies;
DELETE FROM strategy_results;
DELETE FROM system_logs;
DELETE FROM data_update_history;
DELETE FROM job_logs;
DELETE FROM task_execution_details;
```

## 恢复备份（如需要）

### 恢复SQLite数据库

```bash
# 从备份恢复
cp {self.backup_dir}/stock_analysis.db_backup_YYYYMMDD_HHMMSS.db {sqlite_path}
```

### 恢复配置文件

```bash
# 从备份恢复
cp {self.backup_dir}/config_backup_YYYYMMDD_HHMMSS.yaml {project_root}/config.yaml
```

## 常见问题

### 问题1: 应用启动失败

**解决方案**: 检查数据库路径配置是否正确，确保文件存在且有读写权限

### 问题2: 数据加载异常

**解决方案**: 检查SQLite数据库文件是否完整，可以使用sqlite3命令检查表结构

### 问题3: 配置文件格式错误

**解决方案**: 从备份恢复配置文件，或使用YAML格式验证工具检查

## 联系支持

如遇到无法解决的问题，请:
1. 查看应用日志文件
2. 记录错误信息和操作步骤
3. 联系技术支持
"""

        with open(guide_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"手动恢复指南已生成: {guide_file}")
        print(f"\n✓ 手动恢复指南已生成: {guide_file}")
        
        return guide_file


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='迁移回滚工具')
    parser.add_argument('--clear-mysql', action='store_true', help='回滚时清空MySQL数据')
    parser.add_argument('--guide-only', action='store_true', help='仅生成手动恢复指南')
    
    args = parser.parse_args()
    
    try:
        rollback = MigrationRollback()
        
        if args.guide_only:
            # 仅生成恢复指南
            print("生成手动恢复指南...")
            rollback.generate_manual_recovery_guide()
            sys.exit(0)
        
        # 执行完整回滚
        success = rollback.rollback(clear_mysql=args.clear_mysql)
        
        # 生成恢复指南
        rollback.generate_manual_recovery_guide()
        
        # 返回退出码
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n回滚被用户中断")
        sys.exit(130)
    except Exception as e:
        logger.error(f"回滚失败: {e}", exc_info=True)
        print(f"\n错误: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
