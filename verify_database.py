#!/usr/bin/env python3
"""验证数据库表结构"""
import pymysql
from app.utils import get_config

def main():
    config = get_config()
    mysql_config = config.get('database', {}).get('mysql', {})
    
    # 连接数据库
    conn = pymysql.connect(
        host=mysql_config['host'],
        port=mysql_config['port'],
        user=mysql_config['username'],
        password=mysql_config['password'],
        database=mysql_config['database'],
        charset=mysql_config['charset']
    )
    
    cursor = conn.cursor()
    
    print("=" * 60)
    print(f"数据库: {mysql_config['database']}")
    print("=" * 60)
    
    # 查看所有表
    cursor.execute('SHOW TABLES')
    tables = cursor.fetchall()
    
    print(f"\n共找到 {len(tables)} 个表：\n")
    
    for table in tables:
        table_name = table[0]
        
        # 获取表记录数
        cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
        count = cursor.fetchone()[0]
        
        # 获取表结构
        cursor.execute(f'DESCRIBE {table_name}')
        columns = cursor.fetchall()
        
        print(f"表名: {table_name}")
        print(f"  记录数: {count}")
        print(f"  字段数: {len(columns)}")
        print()
    
    conn.close()
    
    print("=" * 60)
    print("数据库验证完成！")
    print("=" * 60)

if __name__ == '__main__':
    main()
