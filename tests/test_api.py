"""
API接口测试脚本
"""
import sys
import time
import requests
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_api(base_url='http://localhost:5000'):
    """测试API接口"""
    
    print("=" * 60)
    print("API接口测试")
    print("=" * 60)
    
    # 1. 测试根路径
    print("\n1. 测试根路径 GET /")
    try:
        response = requests.get(f"{base_url}/")
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ 系统名称: {data['name']}")
            print(f"   ✓ 版本: {data['version']}")
            print(f"   ✓ 状态: {data['status']}")
        else:
            print(f"   ✗ 请求失败")
    except Exception as e:
        print(f"   ✗ 错误: {e}")
    
    # 2. 测试健康检查
    print("\n2. 测试健康检查 GET /health")
    try:
        response = requests.get(f"{base_url}/health")
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ 状态: {data['status']}")
            print(f"   ✓ SQLite: {data['database']['sqlite']}")
            print(f"   ✓ DuckDB: {data['database']['duckdb']}")
        else:
            print(f"   ✗ 请求失败")
    except Exception as e:
        print(f"   ✗ 错误: {e}")
    
    # 3. 测试系统信息
    print("\n3. 测试系统信息 GET /api/system/info")
    try:
        response = requests.get(f"{base_url}/api/system/info")
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                print(f"   ✓ 系统名称: {data['data']['name']}")
                print(f"   ✓ 数据源: {data['data']['datasource']}")
            else:
                print(f"   ✗ 请求失败: {data.get('error')}")
        else:
            print(f"   ✗ 请求失败")
    except Exception as e:
        print(f"   ✗ 错误: {e}")
    
    # 4. 测试系统统计
    print("\n4. 测试系统统计 GET /api/system/stats")
    try:
        response = requests.get(f"{base_url}/api/system/stats")
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                stats = data['data']
                print(f"   ✓ 股票总数: {stats['stocks']['total']}")
                print(f"   ✓ 策略总数: {stats['strategies']['total']}")
                print(f"   ✓ 启用策略: {stats['strategies']['enabled']}")
                print(f"   ✓ 行情记录: {stats['market_data']['record_count']}")
            else:
                print(f"   ✗ 请求失败: {data.get('error')}")
        else:
            print(f"   ✗ 请求失败")
    except Exception as e:
        print(f"   ✗ 错误: {e}")
    
    # 5. 测试股票列表
    print("\n5. 测试股票列表 GET /api/stocks?limit=5")
    try:
        response = requests.get(f"{base_url}/api/stocks?limit=5")
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                print(f"   ✓ 返回数量: {data['count']}")
                print(f"   ✓ 总数: {data['pagination']['total']}")
                if data['data']:
                    stock = data['data'][0]
                    print(f"   ✓ 示例: {stock['code']} - {stock['name']}")
            else:
                print(f"   ✗ 请求失败: {data.get('error')}")
        else:
            print(f"   ✗ 请求失败")
    except Exception as e:
        print(f"   ✗ 错误: {e}")
    
    # 6. 测试策略列表
    print("\n6. 测试策略列表 GET /api/strategies")
    try:
        response = requests.get(f"{base_url}/api/strategies")
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                print(f"   ✓ 策略数量: {data['count']}")
                if data['data']:
                    strategy = data['data'][0]
                    print(f"   ✓ 示例: {strategy['name']}")
                    print(f"   ✓ 启用状态: {strategy['enabled']}")
            else:
                print(f"   ✗ 请求失败: {data.get('error')}")
        else:
            print(f"   ✗ 请求失败")
    except Exception as e:
        print(f"   ✗ 错误: {e}")
    
    # 7. 测试创建策略
    print("\n7. 测试创建策略 POST /api/strategies")
    try:
        payload = {
            'name': 'API测试策略',
            'description': '通过API创建的测试策略',
            'rise_threshold': 6.0,
            'observation_days': 3,
            'ma_period': 5,
            'enabled': True
        }
        response = requests.post(f"{base_url}/api/strategies", json=payload)
        print(f"   状态码: {response.status_code}")
        if response.status_code == 201:
            data = response.json()
            if data['success']:
                strategy_id = data['data']['id']
                print(f"   ✓ 策略创建成功，ID: {strategy_id}")
                
                # 8. 测试获取策略详情
                print(f"\n8. 测试获取策略详情 GET /api/strategies/{strategy_id}")
                response = requests.get(f"{base_url}/api/strategies/{strategy_id}")
                if response.status_code == 200:
                    data = response.json()
                    if data['success']:
                        strategy = data['data']
                        print(f"   ✓ 策略名称: {strategy['name']}")
                        print(f"   ✓ 涨幅阈值: {strategy['rise_threshold']}%")
                        print(f"   ✓ 观察天数: {strategy['observation_days']}")
                    else:
                        print(f"   ✗ 请求失败: {data.get('error')}")
                
                # 9. 测试更新策略
                print(f"\n9. 测试更新策略 PUT /api/strategies/{strategy_id}")
                payload = {'description': '更新后的描述'}
                response = requests.put(f"{base_url}/api/strategies/{strategy_id}", json=payload)
                if response.status_code == 200:
                    data = response.json()
                    if data['success']:
                        print(f"   ✓ 策略更新成功")
                    else:
                        print(f"   ✗ 更新失败: {data.get('error')}")
                
                # 10. 测试禁用策略
                print(f"\n10. 测试禁用策略 POST /api/strategies/{strategy_id}/disable")
                response = requests.post(f"{base_url}/api/strategies/{strategy_id}/disable")
                if response.status_code == 200:
                    data = response.json()
                    if data['success']:
                        print(f"   ✓ 策略已禁用")
                    else:
                        print(f"   ✗ 禁用失败: {data.get('error')}")
                
                # 11. 测试删除策略
                print(f"\n11. 测试删除策略 DELETE /api/strategies/{strategy_id}")
                response = requests.delete(f"{base_url}/api/strategies/{strategy_id}")
                if response.status_code == 200:
                    data = response.json()
                    if data['success']:
                        print(f"   ✓ 策略删除成功")
                    else:
                        print(f"   ✗ 删除失败: {data.get('error')}")
            else:
                print(f"   ✗ 创建失败: {data.get('error')}")
        else:
            print(f"   ✗ 请求失败")
    except Exception as e:
        print(f"   ✗ 错误: {e}")
    
    # 12. 测试调度器任务列表
    print("\n12. 测试调度器任务列表 GET /api/system/scheduler/jobs")
    try:
        response = requests.get(f"{base_url}/api/system/scheduler/jobs")
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                print(f"   ✓ 任务数量: {data['count']}")
                if data['data']:
                    job = data['data'][0]
                    print(f"   ✓ 示例: {job['name']}")
            else:
                print(f"   ✗ 请求失败: {data.get('error')}")
        else:
            print(f"   ✗ 请求失败")
    except Exception as e:
        print(f"   ✗ 错误: {e}")
    
    print("\n" + "=" * 60)
    print("✓ API接口测试完成！")
    print("=" * 60)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='API接口测试')
    parser.add_argument('--url', default='http://localhost:5000', help='API服务器地址')
    args = parser.parse_args()
    
    print(f"测试API服务器: {args.url}")
    print("请确保API服务器已启动（运行 python3 run_api.py）")
    print()
    
    # 等待用户确认
    input("按Enter键开始测试...")
    
    test_api(args.url)


if __name__ == '__main__':
    main()
