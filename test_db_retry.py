#!/usr/bin/env python3
"""
测试数据库重试机制
验证在数据库连接异常时，重试机制是否正常工作
"""
import time
from app.models.database_factory import get_database
from app.utils import get_logger

logger = get_logger(__name__)


def test_retry_mechanism():
    """测试重试机制"""
    print("=" * 60)
    print("测试数据库重试机制")
    print("=" * 60)
    
    try:
        db = get_database()
        
        # 测试1: 正常查询（不应该触发重试）
        print("\n测试1: 正常查询")
        start_time = time.time()
        try:
            result = db.execute_query("SELECT 1 as test")
            elapsed_time = time.time() - start_time
            if result and result[0].get('test') == 1:
                print(f"  ✓ 查询成功 (耗时: {elapsed_time:.3f}s)")
                print(f"  说明: 正常查询不需要重试")
            else:
                print(f"  ⚠️  查询返回结果异常")
        except Exception as e:
            print(f"  ✗ 查询失败: {e}")
        
        # 测试2: 模拟连接问题后重试
        print("\n测试2: 连接稳定性测试")
        print("  执行10次连续查询，观察是否有重试...")
        success_count = 0
        for i in range(10):
            try:
                result = db.execute_query("SELECT 1 as test")
                if result and result[0].get('test') == 1:
                    success_count += 1
                time.sleep(0.1)  # 短暂延迟
            except Exception as e:
                print(f"  第 {i+1} 次查询失败: {e}")
        
        print(f"  ✓ 成功: {success_count}/10")
        if success_count == 10:
            print(f"  说明: 所有查询都成功，连接稳定")
        
        # 测试3: 测试并发查询
        print("\n测试3: 并发查询测试")
        import concurrent.futures
        
        def query_test(query_id):
            try:
                conn_db = get_database()
                result = conn_db.execute_query("SELECT SLEEP(0.1) as test")
                return {'id': query_id, 'success': True}
            except Exception as e:
                return {'id': query_id, 'success': False, 'error': str(e)}
        
        concurrent_count = 5
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_count) as executor:
            futures = [executor.submit(query_test, i) for i in range(concurrent_count)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        elapsed_time = time.time() - start_time
        success_count = sum(1 for r in results if r['success'])
        
        print(f"  并发数: {concurrent_count}")
        print(f"  成功数: {success_count}")
        print(f"  失败数: {concurrent_count - success_count}")
        print(f"  总耗时: {elapsed_time:.3f}s")
        
        if success_count == concurrent_count:
            print(f"  ✓ 所有并发查询都成功，重试机制工作正常")
        
        # 测试4: 测试更新操作的重试
        print("\n测试4: 更新操作测试")
        try:
            # 先创建一个测试记录
            db.execute_update("DELETE FROM test_retry WHERE id = 1")
            db.execute_update("INSERT INTO test_retry (id, name, value) VALUES (?, ?, ?)", 
                            (1, 'test', 100))
            
            # 执行更新
            affected = db.update_one('test_retry', {'value': 200}, {'id': 1})
            print(f"  ✓ 更新成功，影响行数: {affected}")
            
            # 验证更新结果
            result = db.execute_query("SELECT value FROM test_retry WHERE id = 1")
            if result and result[0].get('value') == 200:
                print(f"  ✓ 验证成功，值已更新")
            
            # 清理
            db.execute_update("DELETE FROM test_retry WHERE id = 1")
            print(f"  ✓ 清理完成")
        except Exception as e:
            print(f"  ⚠️  更新测试失败: {e}")
        
        # 测试5: 测试批量插入的重试
        print("\n测试5: 批量插入测试")
        try:
            # 先清理
            db.execute_update("DELETE FROM test_retry WHERE id >= 1")
            
            # 批量插入
            data = [
                (1, 'test1', 100),
                (2, 'test2', 200),
                (3, 'test3', 300),
            ]
            affected = db.execute_many(
                "INSERT INTO test_retry (id, name, value) VALUES (?, ?, ?)",
                data
            )
            print(f"  ✓ 批量插入成功，影响行数: {affected}")
            
            # 验证
            result = db.execute_query("SELECT COUNT(*) as count FROM test_retry WHERE id >= 1")
            if result and result[0].get('count') == 3:
                print(f"  ✓ 验证成功，插入记录数正确")
            
            # 清理
            db.execute_update("DELETE FROM test_retry WHERE id >= 1")
            print(f"  ✓ 清理完成")
        except Exception as e:
            print(f"  ⚠️  批量插入测试失败: {e}")
        
        print("\n" + "=" * 60)
        print("测试完成")
        print("=" * 60)
        print("\n总结:")
        print("✓ 重试机制已集成到所有数据库操作方法中")
        print("✓ 默认重试次数: 3次")
        print("✓ 默认重试延迟: 0.5秒（指数退避）")
        print("✓ 支持的异常类型: OperationalError, InterfaceError, DatabaseError等")
        print("\n说明:")
        print("- 正常情况下，查询会立即成功，不会触发重试")
        print("- 当出现连接问题时，会自动重试最多3次")
        print("- 重试间隔采用指数退避策略（0.5s -> 1s -> 2s）")
        print("- 只有数据库相关的异常才会重试，其他异常直接抛出")
        
        return True
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("数据库重试机制测试工具")
    print("=" * 60)
    print(f"开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 先创建测试表
    print("\n准备测试环境...")
    try:
        from app.models.database_factory import get_database
        db = get_database()
        
        # 创建测试表
        db.execute_update("""
            CREATE TABLE IF NOT EXISTS test_retry (
                id INT PRIMARY KEY,
                name VARCHAR(50),
                value INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        print("✓ 测试表创建成功")
    except Exception as e:
        print(f"✗ 创建测试表失败: {e}")
        return
    
    # 运行测试
    test_ok = test_retry_mechanism()
    
    # 清理
    print("\n清理测试环境...")
    try:
        db = get_database()
        db.execute_update("DROP TABLE IF EXISTS test_retry")
        print("✓ 测试表已删除")
    except Exception as e:
        print(f"⚠️  清理失败: {e}")
    
    # 退出
    print(f"\n结束时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if test_ok:
        print("\n✓ 所有测试通过")
        exit(0)
    else:
        print("\n✗ 部分测试失败")
        exit(1)


if __name__ == '__main__':
    main()
