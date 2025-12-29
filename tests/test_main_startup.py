"""
测试main.py的各种启动方式
"""

import subprocess
import time
import sys

def run_command(cmd, description):
    """运行命令并显示结果"""
    print(f"\n{'=' * 60}")
    print(f"测试: {description}")
    print(f"命令: {cmd}")
    print('=' * 60)
    
    try:
        # 使用 --help 来测试命令是否有效
        result = subprocess.run(
            cmd.split(),
            capture_output=True,
            text=True,
            timeout=5
        )
        
        print(f"返回码: {result.returncode}")
        if result.returncode == 0:
            print("✓ 命令执行成功")
            # 显示前几行输出
            lines = result.stdout.split('\n')[:5]
            for line in lines:
                print(f"  {line}")
        else:
            print("✗ 命令执行失败")
            print(f"错误: {result.stderr}")
        return result.returncode == 0
        
    except Exception as e:
        print(f"✗ 执行异常: {e}")
        return False


def main():
    print("\n股票分析系统 - main.py 启动方式测试")
    print("=" * 60)
    
    tests = [
        ("python main.py --help", "帮助信息"),
        ("python main.py --init-db", "初始化数据库"),
    ]
    
    results = []
    for cmd, desc in tests:
        results.append(run_command(cmd, desc))
    
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    for (cmd, desc), success in zip(tests, results):
        status = "✓ 通过" if success else "✗ 失败"
        print(f"{status} - {desc}")
    
    print("\n" + "=" * 60)
    print("支持的启动方式:")
    print("=" * 60)
    print("1. python main.py              - 启动所有服务（API + Web + 调度器）")
    print("2. python main.py --api-only   - 只启动API服务器")
    print("3. python main.py --web-only   - 只启动Web服务器")
    print("4. python main.py --init-db    - 只初始化数据库")
    print("\n注意: 方式一、二、三会自动初始化数据库")
    print("=" * 60)
    
    if all(results):
        print("\n✓ 所有测试通过！")
        return 0
    else:
        print("\n✗ 部分测试失败")
        return 1


if __name__ == '__main__':
    sys.exit(main())
