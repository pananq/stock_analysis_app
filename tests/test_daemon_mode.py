"""
测试main.py的后台运行和停止功能
"""
import subprocess
import time
import sys
import os

def run_command(cmd, description, timeout=5):
    """运行命令并显示结果"""
    print(f"\n{'=' * 60}")
    print(f"测试: {description}")
    print(f"命令: {cmd}")
    print('=' * 60)
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        print(f"返回码: {result.returncode}")
        
        if result.stdout:
            print(f"标准输出:\n{result.stdout}")
        
        if result.stderr:
            print(f"标准错误:\n{result.stderr}")
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("命令执行超时")
        return False
    except Exception as e:
        print(f"执行异常: {e}")
        return False


def main():
    print("\n股票分析系统 - 后台运行功能测试")
    print("=" * 60)
    
    # 检查是否有服务在运行
    print("\n步骤1: 检查服务状态")
    print("-" * 60)
    run_command("python main.py status", "查看服务状态")
    
    # 如果有服务在运行，先停止
    time.sleep(1)
    print("\n步骤2: 确保服务已停止")
    print("-" * 60)
    run_command("python main.py stop", "停止服务（如果有）")
    time.sleep(2)
    
    # 测试帮助信息
    print("\n步骤3: 查看帮助信息")
    print("-" * 60)
    run_command("python main.py --help", "帮助信息")
    
    # 测试启动服务（前台模式，只做快速验证）
    print("\n步骤4: 测试前台启动命令（3秒后自动停止）")
    print("-" * 60)
    try:
        # 启动进程
        proc = subprocess.Popen(
            ["python", "main.py", "start", "--foreground"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 等待3秒
        print("等待3秒...")
        time.sleep(3)
        
        # 发送中断信号
        print("发送停止信号...")
        proc.send_signal(subprocess.signal.SIGINT)
        
        # 等待进程结束
        try:
            stdout, stderr = proc.communicate(timeout=5)
            print(f"进程已结束，返回码: {proc.returncode}")
            if stdout:
                print(f"输出:\n{stdout}")
        except subprocess.TimeoutExpired:
            proc.kill()
            print("进程超时，已强制杀死")
        
    except Exception as e:
        print(f"测试前台启动失败: {e}")
    
    # 测试状态查看
    print("\n步骤5: 查看服务状态")
    print("-" * 60)
    run_command("python main.py status", "查看服务状态")
    
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print("\n新功能说明:")
    print("1. python main.py           - 后台启动所有服务（默认）")
    print("2. python main.py start     - 后台启动所有服务")
    print("3. python main.py stop      - 停止所有服务")
    print("4. python main.py status    - 查看服务状态")
    print("5. python main.py restart   - 重启所有服务")
    print("6. python main.py start -f  - 前台启动所有服务")
    print("\n其他选项:")
    print("  --api-only: 只启动API服务器")
    print("  --web-only: 只启动Web服务器")
    print("  -f, --foreground: 前台运行")
    print("=" * 60)
    
    print("\n✓ 测试完成！")


if __name__ == '__main__':
    main()
