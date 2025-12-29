#!/usr/bin/env python3
"""测试外键移除后的数据库创建"""
import pymysql
from app.models.orm_models import Base, User, Strategy, StrategyResult, JobLog, TaskExecutionDetail
from app.models.orm_db import ORMDBAdapter
from app.utils import get_config

def main():
    print("=" * 60)
    print("检查 ORM 模型外键定义")
    print("=" * 60)
    
    models = [
        ('User', User),
        ('Strategy', Strategy),
        ('StrategyResult', StrategyResult),
        ('JobLog', JobLog),
        ('TaskExecutionDetail', TaskExecutionDetail)
    ]
    
    has_fk = False
    
    for model_name, model in models:
        print(f'\n模型: {model_name}')
        print(f'  表名: {model.__tablename__}')
        
        # 检查列定义中的外键
        fk_found = False
        for column in model.__table__.columns:
            if column.foreign_keys:
                fk_found = True
                has_fk = True
                print(f'  ⚠️  发现外键: {column.name}')
        
        if not fk_found:
            print(f'  ✓ 无外键')
    
    print('\n' + '=' * 60)
    
    if has_fk:
        print('⚠️  警告：仍然存在外键定义！')
        return False
    else:
        print('✓ 所有模型已成功移除外键')
    
    print("=" * 60)
    print("检查数据库中的外键约束")
    print("=" * 60)
    
    # 检查数据库中的实际外键约束
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
        
        # 查询外键约束
        cursor.execute("""
            SELECT 
                TABLE_NAME,
                COLUMN_NAME,
                CONSTRAINT_NAME,
                REFERENCED_TABLE_NAME,
                REFERENCED_COLUMN_NAME
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = %s
            AND REFERENCED_TABLE_NAME IS NOT NULL
        """, (mysql_config.get('database'),))
        
        foreign_keys = cursor.fetchall()
        
        if foreign_keys:
            print(f'\n⚠️  数据库中发现 {len(foreign_keys)} 个外键约束：\n')
            for fk in foreign_keys:
                print(f'  表: {fk[0]}.{fk[1]}')
                print(f'    引用: {fk[3]}.{fk[4]}')
                print(f'    约束名: {fk[2]}')
                print()
            
            conn.close()
            return False
        else:
            print('\n✓ 数据库中没有外键约束')
            conn.close()
            return True
            
    except Exception as e:
        print(f'\n⚠️  检查数据库外键时出错: {e}')
        return False

if __name__ == '__main__':
    success = main()
    print('\n' + '=' * 60)
    if success:
        print('✓ 外键移除验证通过！')
    else:
        print('⚠️  外键移除验证失败，需要进一步处理')
    print("=" * 60)
    
    exit(0 if success else 1)
