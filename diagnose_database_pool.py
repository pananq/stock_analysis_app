#!/usr/bin/env python3
"""
数据库连接池诊断工具
用于诊断和监控数据库连接池的状态
"""
import time
from sqlalchemy import text
from app.models.database_factory import get_database
from app.utils import get_config, get_logger

logger = get_logger(__name__)


def diagnose_connection_pool():
    """诊断数据库连接池状态"""
    print("=" * 60)
    print("数据库连接池诊断")
    print("=" * 60)
    
    try:
        # 获取配置信息
        config = get_config()
        pool_config = config.get('database', {}).get('mysql', {}).get('pool', {})
        
        print(f"\n连接池配置:")
        print(f"  池大小 (size): {pool_config.get('size', 10)}")
        print(f"  最大溢出 (max_overflow): {pool_config.get('max_overflow', 20)}")
        print(f"  超时时间 (timeout): {pool_config.get('timeout', 30)}s")
        print(f"  回收时间 (recycle): {pool_config.get('recycle', 3600)}s")
        
        # 获取数据库实例
        db = get_database()
        
        if hasattr(db, 'orm_db') and hasattr(db.orm_db, 'engine'):
            engine = db.orm_db.engine
            pool = engine.pool
            
            print(f"\n当前连接池状态:")
            print(f"  池类型: {pool.__class__.__name__}")
            print(f"  活跃连接: {pool.checkedout()}")
            print(f"  空闲连接: {pool.checkedin()}")
            print(f"  总连接数: {pool.checkedout() + pool.checkedin()}")
            print(f"  溢出连接: {pool.overflow()}")
            
            print(f"\n连接池详细信息:")
            print(f"  池大小 (size): {pool.size()}")
            print(f"  溢出连接: {pool.overflow()}")
            print(f"  超时 (timeout): {pool.timeout()}")
            print(f"  回收时间 (recycle): {pool._recycle}")
        
        # 测试数据库连接
        print(f"\n测试数据库连接...")
        start_time = time.time()
        
        try:
            result = db.execute_query("SELECT 1 as test")
            elapsed_time = time.time() - start_time
            
            if result and result[0].get('test') == 1:
                print(f"  ✓ 连接成功 (耗时: {elapsed_time:.3f}s)")
            else:
                print(f"  ⚠️  连接成功但返回结果异常")
        except Exception as e:
            elapsed_time = time.time() - start_time
            print(f"  ✗ 连接失败 (耗时: {elapsed_time:.3f}s)")
            print(f"    错误: {e}")
            return False
        
        # 测试并发连接
        print(f"\n测试并发连接...")
        import concurrent.futures
        
        def test_connection(conn_id):
            try:
                conn_db = get_database()
                result = conn_db.execute_query("SELECT SLEEP(0.1) as test")
                return {'id': conn_id, 'success': True}
            except Exception as e:
                return {'id': conn_id, 'success': False, 'error': str(e)}
        
        concurrent_count = 5
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_count) as executor:
            futures = [executor.submit(test_connection, i) for i in range(concurrent_count)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        elapsed_time = time.time() - start_time
        
        success_count = sum(1 for r in results if r['success'])
        print(f"  并发数: {concurrent_count}")
        print(f"  成功数: {success_count}")
        print(f"  失败数: {concurrent_count - success_count}")
        print(f"  总耗时: {elapsed_time:.3f}s")
        
        if success_count < concurrent_count:
            print(f"\n  ⚠️  部分连接失败:")
            for r in results:
                if not r['success']:
                    print(f"    连接 {r['id']}: {r.get('error', '未知错误')}")
        
        # 检查数据库服务器状态
        print(f"\n检查数据库服务器状态...")
        try:
            # 检查连接数
            result = db.execute_query("SHOW STATUS LIKE 'Threads_connected'")
            if result:
                threads = int(result[0].get('Value', 0))
                print(f"  当前连接数: {threads}")
            
            # 检查最大连接数
            result = db.execute_query("SHOW VARIABLES LIKE 'max_connections'")
            if result:
                max_conn = int(result[0].get('Value', 0))
                print(f"  最大连接数: {max_conn}")
                if threads and max_conn:
                    usage = (threads / max_conn) * 100
                    print(f"  连接使用率: {usage:.1f}%")
                    if usage > 80:
                        print(f"  ⚠️  警告: 连接使用率过高")
            
            # 检查超时设置
            result = db.execute_query("SHOW VARIABLES LIKE 'wait_timeout'")
            if result:
                wait_timeout = result[0].get('Value', 0)
                print(f"  连接超时 (wait_timeout): {wait_timeout}s")
            
        except Exception as e:
            print(f"  ⚠️  无法获取数据库服务器状态: {e}")
        
        return True
        
    except Exception as e:
        print(f"\n✗ 诊断失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_connection_stability():
    """测试连接稳定性"""
    print("\n" + "=" * 60)
    print("连接稳定性测试")
    print("=" * 60)
    
    try:
        db = get_database()
        
        # 执行多次查询
        print(f"\n执行 10 次查询测试...")
        success_count = 0
        fail_count = 0
        
        for i in range(10):
            try:
                result = db.execute_query("SELECT 1 as test")
                if result and result[0].get('test') == 1:
                    success_count += 1
                    print(f"  第 {i+1} 次: ✓")
                else:
                    fail_count += 1
                    print(f"  第 {i+1} 次: ⚠️  返回结果异常")
            except Exception as e:
                fail_count += 1
                print(f"  第 {i+1} 次: ✗ {e}")
        
        print(f"\n结果: 成功 {success_count} 次, 失败 {fail_count} 次")
        
        # 测试长时间运行的查询
        print(f"\n测试长时间查询...")
        try:
            result = db.execute_query("SELECT SLEEP(2) as test")
            if result:
                print(f"  ✓ 长时间查询成功")
        except Exception as e:
            print(f"  ✗ 长时间查询失败: {e}")
        
        return fail_count == 0
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        return False


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("数据库连接池诊断工具")
    print("=" * 60)
    print(f"开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 诊断连接池
    diagnose_ok = diagnose_connection_pool()
    
    # 测试连接稳定性
    stability_ok = test_connection_stability()
    
    print("\n" + "=" * 60)
    print("诊断总结")
    print("=" * 60)
    
    if diagnose_ok and stability_ok:
        print("✓ 所有测试通过，数据库连接池工作正常")
        exit(0)
    else:
        print("⚠️  发现问题，请检查上述错误信息")
        if not diagnose_ok:
            print("  - 连接池诊断失败")
        if not stability_ok:
            print("  - 连接稳定性测试失败")
        exit(1)


if __name__ == '__main__':
    main()
