#!/usr/bin/env python3
# Legacy test retained for migration reference.
"""
测试脚本：验证 ORM MySQL 功能
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils import get_logger
from app.models.database_factory import get_database

logger = get_logger(__name__)


def test_orm_connection():
    """测试 ORM 数据库连接"""
    print("=" * 60)
    print("测试 ORM MySQL 数据库连接")
    print("=" * 60)
    
    try:
        # 获取数据库实例（使用 ORM）
        db = get_database()
        
        print("\n✅ 数据库初始化成功")
        
        # 测试查询
        result = db.execute_query("SELECT COUNT(*) as count FROM stocks")
        print(f"\n📊 股票记录数: {result[0]['count']}")
        
        # 测试带参数的查询
        result = db.execute_query(
            "SELECT code, name, industry FROM stocks WHERE status = ? LIMIT 5",
            ('normal',)
        )
        print(f"\n📋 前5条股票数据:")
        for stock in result:
            print(f"  {stock['code']} - {stock['name']} ({stock['industry']})")
        
        # 测试插入
        print("\n📝 测试插入...")
        insert_id = db.insert_one('stocks', {
            'code': 'TEST001',
            'name': '测试股票',
            'industry': '测试行业',
            'status': 'normal'
        })
        print(f"  插入成功，ID: {insert_id}")
        
        # 测试更新
        print("\n✏️  测试更新...")
        updated = db.update_one('stocks', 
            {'name': '测试股票-已更新'}, 
            {'code': 'TEST001'}
        )
        print(f"  更新成功，影响行数: {updated}")
        
        # 测试删除
        print("\n🗑️  测试删除...")
        deleted = db.delete('stocks', {'code': 'TEST001'})
        print(f"  删除成功，影响行数: {deleted}")
        
        print("\n" + "=" * 60)
        print("✅ 所有测试通过！ORM MySQL 正常工作")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_orm_models():
    """测试直接使用 ORM 模型"""
    print("\n" + "=" * 60)
    print("测试 ORM 模型直接访问")
    print("=" * 60)
    
    try:
        from app.models.orm_models import Stock, Strategy
        from app.models.orm_db import ORMDBAdapter
        from app.utils import get_config
        
        config = get_config()
        mysql_config = config.get('database.mysql')
        mysql_db = ORMDBAdapter('mysql', mysql_config)
        
        session = mysql_db.get_session()
        
        # 查询所有股票
        stocks = session.query(Stock).limit(5).all()
        print(f"\n📊 使用ORM查询股票（前5条）:")
        for stock in stocks:
            print(f"  {stock.code} - {stock.name} - {stock.industry}")
        
        # 查询所有策略
        strategies = session.query(Strategy).all()
        print(f"\n🎯 使用ORM查询策略（共{len(strategies)}条）:")
        for strategy in strategies:
            print(f"  {strategy.id}. {strategy.name} - 启用: {strategy.enabled}")
        
        session.close()
        
        print("\n✅ ORM 模型测试通过！")
        return True
        
    except Exception as e:
        print(f"\n❌ ORM 模型测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = True
    success = test_orm_connection() and success
    success = test_orm_models() and success
    
    sys.exit(0 if success else 1)
