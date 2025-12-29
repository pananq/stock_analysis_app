"""
Gunicorn 配置文件
用于生产环境部署
"""
import multiprocessing
import os

# 服务器套接字
bind = "0.0.0.0:5000"
backlog = 2048

# 工作进程
workers = multiprocessing.cpu_count() * 2 + 1  # 推荐公式：(2 * CPU核心数) + 1
worker_class = "sync"
worker_connections = 1000
max_requests = 1000  # 每个工作进程处理 1000 个请求后重启，防止内存泄漏
max_requests_jitter = 50  # 随机重启时间，避免所有 worker 同时重启
timeout = 30
keepalive = 2

# 进程命名
proc_name = "stock_analysis_api"

# 日志配置
accesslog = "-"  # 输出到 stdout
errorlog = "-"  # 输出到 stderr
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# 进程管理
daemon = False  # 使用 systemd 管理，不使用 Gunicorn 的守护进程模式
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL 配置（如果需要启用 HTTPS，请取消注释并配置证书路径）
# keyfile = "/path/to/ssl/key.pem"
# certfile = "/path/to/ssl/cert.pem"

# 服务器钩子
def on_starting(server):
    """服务器启动前执行"""
    print("Gunicorn 服务器启动中...")

def on_reload(server):
    """重新加载时执行"""
    print("Gunicorn 服务器重新加载中...")

def when_ready(server):
    """服务器就绪时执行"""
    print(f"Gunicorn 服务器已就绪，监听地址: {bind}")

def pre_fork(server, worker):
    """Fork 工作进程前执行"""
    pass

def post_fork(server, worker):
    """Fork 工作进程后执行"""
    pass

def pre_exec(server):
    """新 master 进程 fork 后执行"""
    pass

def worker_int(worker):
    """worker 收到 INT 信号时执行"""
    pass

def worker_abort(worker):
    """worker 异常退出时执行"""
    print(f"Worker {worker.pid} 异常退出!")

def child_exit(server, worker):
    """worker 退出时执行"""
    pass

def worker_exit(server, worker):
    """worker 退出时执行"""
    pass

def nworkers_changed(server, new_value, old_value):
    """worker 数量变化时执行"""
    pass

def on_exit(server):
    """服务器退出时执行"""
    print("Gunicorn 服务器已关闭")
