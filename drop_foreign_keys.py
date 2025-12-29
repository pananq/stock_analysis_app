#!/usr/bin/env python3
"""删除数据库中的所有外键约束"""
import pymysql
from app.utils import get_config

def main():
    print("=" * 60)
    print("删除数据库中的外键约束")
    print("=" * 60)
    
    config = get_config()
    mysql_config = config.get('database', {}).get('mysql', {})
    
    try:
        conn = pymysql.connect(
            host=mysql_config.get('host'),
            port=mysql_config.get('port'),
            user=mysql_config.get('username'),
            password=mysql_config.get('password'),
            database=mysql_config.get('database'),
            charset=mysql_config.get('charset', 'utf8mb4')
        )
        
        cursor = conn.cursor()
        
        # 查询所有外键约束
        cursor.execute("""
            SELECT 
                TABLE_NAME,
                CONSTRAINT_NAME
            FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
            WHERE TABLE_SCHEMA = %s
            AND CONSTRAINT_TYPE = 'FOREIGN KEY'
        """, (mysql_config.get('database'),))
        
        foreign_keys = cursor.fetchall()
        
        if not foreign_keys:
            print('\n✓ 数据库中没有外键约束，无需删除')
            conn.close()
            return True
        
        print(f'\n发现 {len(foreign_keys)} 个外键约束：\n')
        
        # 删除每个外键约束
        for fk in foreign_keys:
            table_name = fk[0]
            constraint_name = fk[1]
            
            try:
                # 禁用外键检查
                cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
                
                # 删除外键约束
                drop_sql = f"ALTER TABLE `{table_name}` DROP FOREIGN KEY `{constraint_name}`"
                cursor.execute(drop_sql)
                conn.commit()
                
                print(f'✓ 已删除: {table_name}.{constraint_name}')
                
                # 重新启用外键检查
                cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
                
            except Exception as e:
                print(f'⚠️  删除失败: {table_name}.{constraint_name}')
                print(f'    错误: {e}')
                conn.rollback()
        
        conn.close()
        
        # 验证是否全部删除
        conn = pymysql.connect(
            host=mysql_config.get('host'),
            port=mysql_config.get('port'),
            user=mysql_config.get('username'),
            password=mysql_config.get('password'),
            database=mysql_config.get('database'),
            charset=mysql_config.get('charset', 'utf8mb4')
        )
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
            WHERE TABLE_SCHEMA = %s
            AND CONSTRAINT_TYPE = 'FOREIGN KEY'
        """, (mysql_config.get('database'),))
        
        count = cursor.fetchone()[0]
        conn.close()
        
        print('\n' + '=' * 60)
        if count == 0:
            print('✓ 所有外键约束已成功删除！')
            return True
        else:
            print(f'⚠️  仍有 {count} 个外键约束未删除')
            return False
            
    except Exception as e:
        print(f'\n⚠️  删除外键约束时出错: {e}')
        return False

if __name__ == '__main__':
    success = main()
    print("=" * 60)
    exit(0 if success else 1)
