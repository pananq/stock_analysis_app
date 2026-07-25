"""
股海罗盘主程序
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

# PID文件路径
PID_FILE = project_root / '.stock_app.pid'
LOG_FILE = project_root / 'logs' / 'app.log'


def ensure_initial_admin(auth_service, config) -> bool:
    """按配置创建缺失的初始管理员；服务自身保证已有管理员不被修改。"""
    return auth_service.ensure_admin_exists(
        config.get('auth.initial_admin_password')
    )


def configure_scheduler(scheduler, config) -> bool:
    """按配置注册并启动任务；便于隔离测试启动编排。"""
    settings = config.get('scheduler', {})
    if not settings.get('enabled', True):
        return False

    jobs = settings.get('jobs', {})
    stock_job = jobs.get('stock_update', {})
    if stock_job.get('enabled', True):
        scheduler.add_daily_stock_update_job(
            hour=stock_job.get('hour'),
            minute=stock_job.get('minute'),
        )

    market_job = jobs.get('market_data_update', {})
    if market_job.get('enabled', True):
        scheduler.add_daily_market_data_update_job(
            hour=market_job.get('hour'),
            minute=market_job.get('minute'),
        )

    strategy_job = jobs.get('strategy_execution', {})
    if strategy_job.get('enabled', True):
        scheduler.add_daily_strategy_execution_job(
            hour=strategy_job.get('hour'),
            minute=strategy_job.get('minute'),
        )

    scheduler.add_daily_report_job()

    health_job = jobs.get('health_check', {})
    if health_job.get('enabled', True):
        scheduler.add_periodic_health_check_job(
            interval_minutes=int(health_job.get('interval_minutes', 30))
        )
    scheduler.start()
    return True


def run_api_server():
    """运行API服务器"""
    from app.api import create_app
    from app.scheduler import get_task_scheduler
    
    logger = get_logger(__name__)
    config = get_config()
    
    scheduler = None
    try:
        # 创建Flask应用
        app = create_app(config)
        
        # 启动调度器
        if config.get('scheduler.enabled', True):
            scheduler = get_task_scheduler()
            logger.info("按配置添加定时任务...")
            configure_scheduler(scheduler, config)
            logger.info("调度器已启动")
        else:
            logger.info("调度器已禁用")
        
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
            if scheduler is not None:
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
        
        # 初始化MySQL行情数据库
        from app.services.market_data_service import get_market_data_service
        market_data_service = get_market_data_service()
        stats = market_data_service.get_statistics()
        
        if stats:
            logger.info(f"MySQL行情数据库连接成功")
            logger.info(f"  股票数量: {stats.get('stock_count', 0)}")
            logger.info(f"  记录总数: {stats.get('total_records', 0)}")
            if stats.get('earliest_date'):
                logger.info(f"  日期范围: {stats.get('earliest_date')} ~ {stats.get('latest_date')}")

        # 首次初始化时按显式环境变量创建管理员；已有管理员不会被修改。
        from app.services.auth_service import AuthService
        admin_created = ensure_initial_admin(AuthService(), config)
        if admin_created:
            logger.info("初始管理员已创建")
        
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


def cleanup_pid(force: bool = False):
    """仅由 PID 文件所属进程清理；停止命令可显式 force。"""
    try:
        if PID_FILE.exists():
            if not force:
                try:
                    recorded_pid = int(PID_FILE.read_text().strip())
                except ValueError:
                    return
                if recorded_pid != os.getpid():
                    return
            PID_FILE.unlink()
            print(f"PID文件已删除: {PID_FILE}")
    except Exception as e:
        print(f"删除PID文件失败: {e}")


def is_managed_process(pid: int) -> bool:
    """确认 PID 对应当前项目入口，避免 PID 复用或宽泛扫描误杀其他进程。"""
    import subprocess
    try:
        result = subprocess.run(
            ['ps', '-p', str(pid), '-o', 'command='],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return False
        command = result.stdout.strip()
        absolute_entry = str((project_root / 'main.py').resolve())
        if absolute_entry in command:
            return True
        if 'python' not in command.lower() or 'main.py' not in command:
            return False

        proc_cwd = Path(f'/proc/{pid}/cwd')
        if proc_cwd.exists():
            return proc_cwd.resolve() == project_root.resolve()

        # macOS 没有 /proc，通过 lsof 获取进程工作目录。
        cwd_result = subprocess.run(
            ['lsof', '-a', '-p', str(pid), '-d', 'cwd', '-Fn'],
            capture_output=True,
            text=True,
            check=False,
        )
        cwd_lines = [
            line[1:] for line in cwd_result.stdout.splitlines()
            if line.startswith('n')
        ]
        return bool(cwd_lines) and Path(cwd_lines[0]).resolve() == project_root.resolve()
    except Exception:
        return False


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
    
    # 保存最终守护主进程 PID；停止时再通过 PID 查询实际进程组。
    save_pid(os.getpid())


def stop_services():
    """停止所有服务"""
    print("=" * 60)
    print("停止股海罗盘")
    print("=" * 60)
    
    if not PID_FILE.exists():
        print("未找到PID文件，服务可能未在后台运行")
        return 1
    
    try:
        # PID 文件记录守护主进程；进程组 ID 必须在停止时动态查询。
        pid = int(PID_FILE.read_text().strip())
        print(f"找到服务主进程 PID: {pid}")

        if not is_managed_process(pid):
            print("PID 对应的进程无法确认为本项目，拒绝发送停止信号")
            return 1
        
        # 检查主进程并解析其实际进程组。
        try:
            os.kill(pid, 0)
            pgid = os.getpgid(pid)
            print(f"服务进程组 PGID: {pgid}")
        except OSError:
            print("服务主进程不存在")
            cleanup_pid(force=True)
            return 1
        
        # 尝试优雅停止整个进程组（使用负PID）
        print("正在停止服务...")
        try:
            os.killpg(pgid, signal.SIGTERM)
        except ProcessLookupError:
            print("进程组不存在")
            cleanup_pid(force=True)
            return 1
        
        # 等待进程结束
        max_wait = 10
        for i in range(max_wait):
            time.sleep(1)
            try:
                os.kill(pid, 0)
                print(f"等待进程结束... ({i+1}/{max_wait})")
            except OSError:
                break
        
        # 检查是否已停止
        try:
            os.kill(pid, 0)
            # 强制杀死整个进程组
            print("进程未响应，强制停止...")
            os.killpg(pgid, signal.SIGKILL)
            time.sleep(1)
        except (OSError, ProcessLookupError):
            pass
        
        cleanup_pid(force=True)
        print("服务已停止")
        return 0
        
    except ValueError:
        print("PID文件格式错误")
        cleanup_pid(force=True)
        return 1
    except Exception as e:
        print(f"停止服务失败: {e}")
        return 1


def status_services():
    """查看服务状态"""
    print("=" * 60)
    print("股海罗盘状态")
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


def get_runtime_readiness(config) -> dict:
    """生成不读取或输出密钥明文的运行配置检查结果。"""
    from app.services.daily_report_service import get_daily_report_targets
    from app.utils.auth import AuthUtils

    auth_secret = config.get(
        'auth.secret_key',
        config.get('web.secret_key', ''),
    )
    ai_enabled = bool(config.get('ai.enabled', False))
    email_enabled = bool(config.get('notifications.email.enabled', False))
    report_enabled = bool(
        config.get('notifications.daily_report.enabled', False)
    )
    email = config.get('notifications.email', {}) or {}
    targets = get_daily_report_targets(config)
    email_host = str(email.get('host') or '').strip().lower()
    from_address = str(email.get('from_address') or '').strip().lower()
    email_is_configured = (
        bool(email_host)
        and email_host != 'smtp.example.com'
        and bool(from_address)
        and not from_address.endswith('@example.com')
        and bool(targets)
    )
    cors_origins = config.get('api.cors_origins', [])
    cors_is_restricted = bool(cors_origins) and cors_origins != '*'

    return {
        'datasource': {
            'ready': config.get('datasource.type') in {'akshare', 'tushare'},
            'detail': str(config.get('datasource.type') or '未配置'),
        },
        'cors': {
            'ready': cors_is_restricted,
            'detail': (
                '已限制允许的 Web 来源'
                if cors_is_restricted
                else '当前允许任意来源；部署时应限制 api.cors_origins'
            ),
        },
        'auth': {
            'ready': AuthUtils.is_secret_strong(auth_secret),
            'detail': (
                '密钥强度符合要求'
                if AuthUtils.is_secret_strong(auth_secret)
                else '请在 .env 设置至少 32 字符的随机 AUTH_SECRET_KEY'
            ),
        },
        'admin_bootstrap': {
            'ready': AuthUtils.is_password_acceptable(
                config.get('auth.initial_admin_password', '')
            ),
            'detail': (
                '已提供首次管理员密码'
                if AuthUtils.is_password_acceptable(
                    config.get('auth.initial_admin_password', '')
                )
                else '未配置或少于12字符；已有管理员时可忽略'
            ),
        },
        'ai': {
            'ready': ai_enabled and bool(config.get('ai.api_key')),
            'enabled': ai_enabled,
            'detail': (
                f"已启用 · {config.get('ai.model', '未配置模型')}"
                if ai_enabled and config.get('ai.api_key')
                else '已启用但缺少 AI_API_KEY'
                if ai_enabled
                else '未启用'
            ),
        },
        'email': {
            'ready': email_enabled and email_is_configured,
            'enabled': email_enabled,
            'detail': (
                f'已启用 · {len(targets)} 个发送目标'
                if email_enabled and email_is_configured
                else '已启用但 SMTP 或收件人配置不完整'
                if email_enabled
                else '未启用'
            ),
        },
        'daily_report': {
            'ready': report_enabled and email_enabled and email_is_configured,
            'enabled': report_enabled,
            'detail': (
                f"已启用 · 每日 {config.get('notifications.daily_report.time', '20:00')}"
                if report_enabled and email_enabled and email_is_configured
                else '已启用但邮件或发送目标未就绪'
                if report_enabled
                else '未启用'
            ),
        },
    }


def run_doctor() -> int:
    """输出脱敏的运行准备度，不进行网络请求或数据库写入。"""
    try:
        config = get_config()
        readiness = get_runtime_readiness(config)
    except Exception as exc:
        print(f"[ERROR] 配置加载失败: {exc}")
        return 1

    print("股海罗盘运行配置检查")
    labels = {
        'datasource': '行情数据源',
        'cors': 'API 跨域',
        'auth': '认证密钥',
        'admin_bootstrap': '初始管理员',
        'ai': 'AI 分析',
        'email': '邮件通知',
        'daily_report': '定时日报',
    }
    for key, item in readiness.items():
        if item['ready']:
            status = 'OK'
        elif item.get('enabled') is False:
            status = 'OFF'
        elif key in {'admin_bootstrap', 'cors'}:
            status = 'WARN'
        else:
            status = 'ERROR'
        print(f"[{status}] {labels[key]}: {item['detail']}")

    # 认证密钥是所有可访问启动模式的硬要求；其余增强功能可按需关闭。
    return 0 if readiness['auth']['ready'] else 1


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
    parser = argparse.ArgumentParser(description='股海罗盘', formatter_class=argparse.RawDescriptionHelpFormatter)
    
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

    # doctor命令
    subparsers.add_parser('doctor', help='脱敏检查运行配置，不访问外部服务')
    
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

    if args.command == 'doctor':
        sys.exit(run_doctor())
    
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
        readiness = get_runtime_readiness(get_config())
        if not readiness['auth']['ready']:
            print(f"启动前检查失败: {readiness['auth']['detail']}")
            print("可运行 `python main.py doctor` 查看脱敏配置状态。")
            sys.exit(1)

        # 先初始化数据库
        init_databases()
        
        # 设置信号处理
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        # 决定是否后台运行
        if not args.foreground:
            print("\n" + "=" * 60)
            print("启动股海罗盘（后台模式）")
            print("=" * 60)
            daemonize()
            # 只在最终守护子进程注册，避免 fork 父进程退出时误删 PID 文件。
            atexit.register(cleanup_pid)
        else:
            print("\n" + "=" * 60)
            print("启动股海罗盘（前台模式）")
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

            from app.mcp.server import run_mcp_server

            # 使用多进程同时启动API和Web服务器
            # 注意：子进程会继承父进程的进程组ID
            api_process = multiprocessing.Process(target=run_api_server)
            web_process = multiprocessing.Process(target=run_web_server)

            # 启动进程
            api_process.start()
            web_process.start()

            # 启动MCP进程（如果启用）
            mcp_process = None
            if get_config().get('mcp.enabled', True):
                mcp_process = multiprocessing.Process(target=run_mcp_server)
                mcp_process.start()
                logger.info(f"MCP进程 PID: {mcp_process.pid}")

            # 记录子进程信息到日志
            logger.info(f"API进程 PID: {api_process.pid}")
            logger.info(f"Web进程 PID: {web_process.pid}")
            logger.info(f"主进程 PID: {os.getpid()}")
            logger.info(f"进程组 PGID: {os.getpgid(0)}")

            runtime_config = get_config()
            api_port = runtime_config.get('api.port', 5000)
            web_port = runtime_config.get('web.port', 8000)
            mcp_port = runtime_config.get('mcp.port', 5002)
            if not args.foreground:
                logger.info("所有服务已启动！")
                logger.info(f"  - API服务器: http://localhost:{api_port}")
                logger.info(f"  - Web界面:   http://localhost:{web_port}")
                logger.info(
                    f"  - 智能日报:  http://localhost:{web_port}/reports"
                )
                if mcp_process:
                    logger.info(f"  - MCP服务:   http://localhost:{mcp_port}")
            else:
                print("\n所有服务已启动！")
                print(f"  - API服务器: http://localhost:{api_port}")
                print(f"  - Web界面:   http://localhost:{web_port}")
                print(
                    f"  - 智能日报:  http://localhost:{web_port}/reports"
                )
                if mcp_process:
                    print(f"  - MCP服务:   http://localhost:{mcp_port}")
                print("\n按 Ctrl+C 停止所有服务\n")

            # 等待进程结束
            try:
                api_process.join()
                web_process.join()
                if mcp_process:
                    mcp_process.join()
            except KeyboardInterrupt:
                logger.info("\n收到中断信号，正在关闭所有服务...")

                # 终止进程
                api_process.terminate()
                web_process.terminate()
                if mcp_process:
                    mcp_process.terminate()

                # 等待进程结束
                api_process.join(timeout=5)
                web_process.join(timeout=5)
                if mcp_process:
                    mcp_process.join(timeout=5)

                # 如果进程仍在运行，强制杀死
                if api_process.is_alive():
                    api_process.kill()
                if web_process.is_alive():
                    web_process.kill()
                if mcp_process and mcp_process.is_alive():
                    mcp_process.kill()

                logger.info("所有服务已关闭")


if __name__ == '__main__':
    main()
