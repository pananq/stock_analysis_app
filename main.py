"""
股票分析系统主程序
支持启动API服务、Web服务和调度器
"""
import sys
import argparse
import multiprocessing
import os
import signal
import time
import atexit
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.utils import get_config, setup_logging, get_logger
from app.models import get_duckdb

# PID文件路径
PID_FILE = project_root / '.stock_app.pid'
LOG_FILE = project_root / 'logs' / 'app.log'


def run_api_server():
    """运行API服务器"""
    from app.api import create_app
    from app.scheduler import get_task_scheduler
    
    logger = get_logger(__name__)
    config = get_config()
    
    try:
        # 创建Flask应用
        app = create_app(config)
        
        # 启动调度器
        scheduler = get_task_scheduler()
        
        # 添加定时任务
        logger.info("添加定时任务...")
        scheduler.add_daily_stock_update_job(hour=18, minute=0)
        scheduler.add_daily_market_data_update_job(hour=18, minute=30)
        scheduler.add_daily_strategy_execution_job(hour=19, minute=0)
        scheduler.add_periodic_health_check_job(interval_minutes=30)
        
        # 启动调度器
        scheduler.start()
        logger.info("调度器已启动")
        
        # 获取API配置
        api_config = config.get('api', {})
        host = api_config.get('host', '0.0.0.0')
        port = api_config.get('port', 5000)
        debug = api_config.get('debug', False)
        
        logger.info(f"API服务器启动: http://{host}:{port}")
        
        # 启动Flask应用
        app.run(
            host=host,
            port=port,
            debug=debug,
            use_reloader=False
        )
        
    except KeyboardInterrupt:
        logger.info("\n收到中断信号，正在关闭API服务器...")
        try:
            scheduler = get_task_scheduler()
            scheduler.shutdown(wait=True)
            logger.info("调度器已关闭")
        except:
            pass
        logger.info("API服务器已关闭")


def run_web_server():
    """运行Web服务器"""
    from app.web import create_web_app
    
    logger = get_logger(__name__)
    config = get_config()
    
    try:
        # 创建Flask应用
        app = create_web_app(config)
        
        # 获取Web配置
        web_config = config.get('web', {})
        host = web_config.get('host', '0.0.0.0')
        port = web_config.get('port', 8000)
        debug = web_config.get('debug', False)
        
        logger.info(f"Web服务器启动: http://{host}:{port}")
        
        # 启动Flask应用
        app.run(
            host=host,
            port=port,
            debug=debug
        )
        
    except KeyboardInterrupt:
        logger.info("\n收到中断信号，正在关闭Web服务器...")
        logger.info("Web服务器已关闭")


def init_databases():
    """初始化数据库"""
    try:
        config = get_config()
        
        # 初始化日志系统
        setup_logging(config)
        logger = get_logger(__name__)
        
        logger.info("=" * 60)
        logger.info("初始化数据库")
        logger.info("=" * 60)
        
        # 显示配置信息
        logger.info(f"数据源类型: {config.get('datasource.type')}")
        logger.info(f"DuckDB数据库: {config.get('database.duckdb_path')}")
        
        # 初始化DuckDB数据库
        duckdb = get_duckdb()
        logger.info("DuckDB数据库连接成功")
        
        logger.info("数据库初始化完成")
        
    except Exception as e:
        print(f"数据库初始化失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def save_pid(pid):
    """保存进程ID到文件"""
    try:
        PID_FILE.write_text(str(pid))
        print(f"PID文件已创建: {PID_FILE}")
    except Exception as e:
        print(f"保存PID文件失败: {e}")


def cleanup_pid():
    """清理PID文件"""
    try:
        if PID_FILE.exists():
            PID_FILE.unlink()
            print(f"PID文件已删除: {PID_FILE}")
    except Exception as e:
        print(f"删除PID文件失败: {e}")


def kill_all_processes():
    """查找并杀死所有相关的Python进程"""
    import subprocess
    try:
        # 查找所有 main.py 相关的进程
        result = subprocess.run(
            ['ps', 'aux'],
            capture_output=True,
            text=True
        )
        
        killed_count = 0
        for line in result.stdout.split('\n'):
            if 'python' in line and 'main.py' in line and 'grep' not in line:
                parts = line.split()
                if len(parts) > 1:
                    try:
                        pid = int(parts[1])
                        # 不要杀死当前进程
                        if pid != os.getpid():
                            os.kill(pid, signal.SIGKILL)
                            killed_count += 1
                            print(f"已杀死进程: {pid}")
                    except (ValueError, ProcessLookupError, PermissionError):
                        pass
        
        if killed_count > 0:
            print(f"共杀死 {killed_count} 个相关进程")
    except Exception as e:
        print(f"清理进程失败: {e}")


def daemonize():
    """将进程转为后台守护进程"""
    try:
        # 第一次fork
        pid = os.fork()
        if pid > 0:
            # 父进程退出
            print(f"服务正在后台运行，PID: {pid}")
            sys.exit(0)
    except OSError as e:
        print(f"第一次fork失败: {e}")
        sys.exit(1)
    
    # 脱离控制终端，创建新的会话和进程组
    os.setsid()
    
    # 第二次fork
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except OSError as e:
        print(f"第二次fork失败: {e}")
        sys.exit(1)
    
    # 重定向标准输入输出
    sys.stdout.flush()
    sys.stderr.flush()
    
    # 重定向到日志文件
    log_dir = LOG_FILE.parent
    if not log_dir.exists():
        log_dir.mkdir(parents=True, exist_ok=True)
    
    # 打开日志文件
    sys.stdin = open(os.devnull, 'r')
    sys.stdout = open(LOG_FILE, 'a+')
    sys.stderr = open(LOG_FILE, 'a+')
    
    # 保存当前进程组ID（使用当前进程PID作为进程组ID）
    save_pid(os.getpid())


def stop_services():
    """停止所有服务"""
    print("=" * 60)
    print("停止股票分析系统")
    print("=" * 60)
    
    if not PID_FILE.exists():
        print("未找到PID文件，服务可能未在后台运行")
        # 尝试查找并杀死所有相关进程
        kill_all_processes()
        return 1
    
    try:
        # 读取PID（进程组ID）
        pgid = int(PID_FILE.read_text().strip())
        print(f"找到服务进程组 PGID: {pgid}")
        
        # 检查进程组是否存在
        try:
            os.kill(pgid, 0)  # 发送信号0检查进程是否存在
        except OSError:
            print("进程组不存在")
            cleanup_pid()
            # 尝试查找并杀死所有相关进程
            kill_all_processes()
            return 1
        
        # 尝试优雅停止整个进程组（使用负PID）
        print("正在停止服务...")
        try:
            os.killpg(pgid, signal.SIGTERM)
        except ProcessLookupError:
            print("进程组不存在")
            cleanup_pid()
            kill_all_processes()
            return 1
        
        # 等待进程结束
        max_wait = 10
        for i in range(max_wait):
            time.sleep(1)
            try:
                os.kill(pgid, 0)
                print(f"等待进程结束... ({i+1}/{max_wait})")
            except OSError:
                break
        
        # 检查是否已停止
        try:
            os.kill(pgid, 0)
            # 强制杀死整个进程组
            print("进程未响应，强制停止...")
            os.killpg(pgid, signal.SIGKILL)
            time.sleep(1)
        except (OSError, ProcessLookupError):
            pass
        
        # 确保所有相关进程都被杀死
        kill_all_processes()
        
        cleanup_pid()
        print("服务已停止")
        return 0
        
    except ValueError:
        print("PID文件格式错误")
        cleanup_pid()
        kill_all_processes()
        return 1
    except Exception as e:
        print(f"停止服务失败: {e}")
        kill_all_processes()
        return 1


def status_services():
    """查看服务状态"""
    print("=" * 60)
    print("股票分析系统状态")
    print("=" * 60)
    
    if not PID_FILE.exists():
        print("状态: 未运行")
        return
    
    try:
        pid = int(PID_FILE.read_text().strip())
        
        # 检查进程是否存在
        try:
            os.kill(pid, 0)
            print(f"状态: 运行中")
            print(f"PID: {pid}")
            print(f"日志文件: {LOG_FILE}")
            
            # 显示最后几行日志
            if LOG_FILE.exists():
                print("\n最近的日志:")
                try:
                    with open(LOG_FILE, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        if lines:
                            for line in lines[-5:]:
                                print(f"  {line.rstrip()}")
                        else:
                            print("  (日志文件为空)")
                except Exception as e:
                    print(f"  读取日志失败: {e}")
        except OSError:
            print("状态: 进程不存在（PID文件残留）")
            print("建议运行: python main.py stop")
    except ValueError:
        print("状态: PID文件格式错误")
    except Exception as e:
        print(f"状态: 未知错误 ({e})")


def signal_handler(signum, frame):
    """信号处理函数"""
    print(f"收到信号 {signum}，正在关闭服务...")
    
    # 关闭调度器
    try:
        from app.scheduler import get_task_scheduler
        scheduler = get_task_scheduler()
        scheduler.shutdown(wait=False)
    except:
        pass
    
    # 清理PID文件
    cleanup_pid()
    
    sys.exit(0)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='股票分析系统', formatter_class=argparse.RawDescriptionHelpFormatter)
    
    # 子命令
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # start命令
    start_parser = subparsers.add_parser('start', help='启动服务')
    start_parser.add_argument('--api-only', action='store_true', help='只启动API服务器')
    start_parser.add_argument('--web-only', action='store_true', help='只启动Web服务器')
    start_parser.add_argument('--foreground', '-f', action='store_true', help='前台运行（默认后台运行）')
    
    # stop命令
    subparsers.add_parser('stop', help='停止服务')
    
    # status命令
    subparsers.add_parser('status', help='查看服务状态')
    
    # restart命令
    restart_parser = subparsers.add_parser('restart', help='重启服务')
    restart_parser.add_argument('--api-only', action='store_true', help='只重启API服务器')
    restart_parser.add_argument('--web-only', action='store_true', help='只重启Web服务器')
    restart_parser.add_argument('--foreground', '-f', action='store_true', help='前台运行')
    
    # 兼容旧版本的参数
    parser.add_argument('--api-only', action='store_true', help='只启动API服务器（兼容旧版）')
    parser.add_argument('--web-only', action='store_true', help='只启动Web服务器（兼容旧版）')
    parser.add_argument('--init-db', action='store_true', help='只初始化数据库（兼容旧版）')
    
    args = parser.parse_args()
    
    # 如果没有指定命令，默认执行start
    if args.command is None:
        # 兼容旧版本：如果没有参数，默认前台启动所有服务
        if args.init_db:
            init_databases()
            print("数据库初始化完成")
            return
        else:
            # 默认后台启动所有服务
            args.command = 'start'
            args.foreground = False
    
    # 处理stop命令
    if args.command == 'stop':
        sys.exit(stop_services())
    
    # 处理status命令
    if args.command == 'status':
        status_services()
        return
    
    # 处理restart命令
    if args.command == 'restart':
        print("正在重启服务...")
        stop_services()
        time.sleep(2)  # 等待进程完全停止
        args.command = 'start'
        if not hasattr(args, 'foreground'):
            args.foreground = False
    
    # 处理start命令
    if args.command == 'start':
        # 先初始化数据库
        init_databases()
        
        # 设置信号处理
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        # 注册清理函数
        atexit.register(cleanup_pid)
        
        # 决定是否后台运行
        if not args.foreground:
            print("\n" + "=" * 60)
            print("启动股票分析系统（后台模式）")
            print("=" * 60)
            daemonize()
        else:
            print("\n" + "=" * 60)
            print("启动股票分析系统（前台模式）")
            print("=" * 60)
        
        logger = get_logger(__name__)
        
        # 根据参数决定启动哪些服务
        if args.api_only:
            logger.info("启动API服务器（含调度器）")
            run_api_server()
        elif args.web_only:
            logger.info("启动Web服务器")
            run_web_server()
        else:
            logger.info("启动所有服务（API + Web + 调度器）")
            
            # 使用多进程同时启动API和Web服务器
            # 注意：子进程会继承父进程的进程组ID
            api_process = multiprocessing.Process(target=run_api_server)
            web_process = multiprocessing.Process(target=run_web_server)
            
            # 启动进程
            api_process.start()
            web_process.start()
            
            # 记录子进程信息到日志
            logger.info(f"API进程 PID: {api_process.pid}")
            logger.info(f"Web进程 PID: {web_process.pid}")
            logger.info(f"主进程 PID: {os.getpid()}")
            logger.info(f"进程组 PGID: {os.getpgid(0)}")
            
            if not args.foreground:
                logger.info("所有服务已启动！")
                logger.info(f"  - API服务器: http://localhost:5000")
                logger.info(f"  - Web界面:   http://localhost:8000")
                logger.info(f"  - API文档:   http://localhost:5000/api/docs")
            else:
                print("\n所有服务已启动！")
                print(f"  - API服务器: http://localhost:5000")
                print(f"  - Web界面:   http://localhost:8000")
                print(f"  - API文档:   http://localhost:5000/api/docs")
                print("\n按 Ctrl+C 停止所有服务\n")
            
            # 等待进程结束
            try:
                api_process.join()
                web_process.join()
            except KeyboardInterrupt:
                logger.info("\n收到中断信号，正在关闭所有服务...")
                
                # 终止进程
                api_process.terminate()
                web_process.terminate()
                
                # 等待进程结束
                api_process.join(timeout=5)
                web_process.join(timeout=5)
                
                # 如果进程仍在运行，强制杀死
                if api_process.is_alive():
                    api_process.kill()
                if web_process.is_alive():
                    web_process.kill()
                
                logger.info("所有服务已关闭")


if __name__ == '__main__':
    main()
