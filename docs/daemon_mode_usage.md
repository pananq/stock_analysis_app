# main.py 后台运行功能使用指南

## 概述

`main.py` 现已升级为支持后台运行的守护进程管理工具，提供完整的启动、停止、状态查看和重启功能。

## 快速开始

### 启动服务（后台模式）

```bash
# 默认启动所有服务（API + Web + 调度器）
python main.py

# 或使用显式命令
python main.py start
```

服务将在后台运行，立即返回命令行提示符。

### 停止服务

```bash
python main.py stop
```

### 查看服务状态

```bash
python main.py status
```

### 重启服务

```bash
python main.py restart
```

## 完整命令列表

### 1. 启动服务

```bash
# 启动所有服务（后台模式，默认）
python main.py start

# 启动所有服务（前台模式，可看到实时日志）
python main.py start --foreground
python main.py start -f

# 只启动API服务器（含调度器）
python main.py start --api-only

# 只启动Web服务器
python main.py start --web-only
```

### 2. 停止服务

```bash
# 停止所有服务
python main.py stop
```

停止逻辑：
1. 发送 SIGTERM 信号（优雅停止）
2. 等待最多10秒
3. 如果进程未响应，发送 SIGKILL 信号（强制停止）

### 3. 查看状态

```bash
python main.py status
```

输出示例：
```
============================================================
股票分析系统状态
============================================================
状态: 运行中
PID: 3045584
日志文件: /data/home/aaronpan/stock-analysis-app/logs/app.log

最近的日志:
  2025-12-26 10:38:51 - INFO - 启动所有服务（API + Web + 调度器）
  2025-12-26 10:38:51 - INFO - 所有服务已启动！
  2025-12-26 10:38:51 - INFO -   - API服务器: http://localhost:5000
```

### 4. 重启服务

```bash
# 重启所有服务
python main.py restart

# 重启并指定模式
python main.py restart --foreground
python main.py restart --api-only
```

### 5. 查看帮助

```bash
# 主帮助
python main.py --help

# start命令帮助
python main.py start --help

# restart命令帮助
python main.py restart --help
```

## 与旧版本的兼容性

为了保持兼容性，以下旧版本命令仍然可用：

```bash
# 初始化数据库（不启动服务）
python main.py --init-db

# 前台启动所有服务
python main.py --api-only
python main.py --web-only
```

注意：不带任何参数的 `python main.py` 现在默认后台启动，而不是前台启动。

## 技术实现

### 守护进程机制

使用双 fork 技术实现守护进程：

```python
def daemonize():
    # 第一次fork：父进程退出，子进程成为孤儿进程
    pid = os.fork()
    if pid > 0:
        sys.exit(0)
    
    # 创建新会话，脱离控制终端
    os.setsid()
    
    # 第二次fork：子进程退出，孙子进程成为真正的守护进程
    pid = os.fork()
    if pid > 0:
        sys.exit(0)
    
    # 重定向标准输入输出到日志文件
    sys.stdin = open(os.devnull, 'r')
    sys.stdout = open(LOG_FILE, 'a+')
    sys.stderr = open(LOG_FILE, 'a+')
```

### PID 文件管理

- **位置**: `.stock_app.pid`（项目根目录）
- **内容**: 主进程的PID
- **作用**: 跟踪服务进程，支持stop和status命令

### 日志文件

- **位置**: `logs/app.log`（自动创建）
- **内容**: 所有服务的输出和错误日志
- **查看**: `tail -f logs/app.log` 或使用 `python main.py status`

### 信号处理

支持以下信号：

| 信号 | 处理方式 |
|------|----------|
| SIGTERM | 优雅停止（stop命令使用） |
| SIGINT | 前台模式下的Ctrl+C |
| SIGKILL | 强制停止（stop命令在超时后使用） |

## 使用场景

### 开发环境

```bash
# 前台运行，实时查看日志
python main.py start --foreground

# 或只启动API进行后端开发
python main.py start --api-only --foreground
```

### 生产环境

```bash
# 后台启动所有服务
python main.py start

# 查看服务状态
python main.py status

# 如需重启
python main.py restart

# 如需停止
python main.py stop
```

### 定时任务管理

服务启动后会自动创建以下定时任务：

- **18:00** - 更新股票数据
- **18:30** - 更新市场数据
- **19:00** - 执行策略分析
- **每30分钟** - 健康检查

## 故障排查

### 服务无法启动

1. 检查端口是否被占用：
   ```bash
   lsof -i :5000  # API端口
   lsof -i :8000  # Web端口
   ```

2. 查看日志文件：
   ```bash
   tail -50 logs/app.log
   ```

3. 尝试前台启动查看详细错误：
   ```bash
   python main.py start --foreground
   ```

### 服务无法停止

1. 检查PID文件：
   ```bash
   cat .stock_app.pid
   ```

2. 手动检查进程：
   ```bash
   ps -p <PID>
   ```

3. 强制杀死进程：
   ```bash
   kill -9 <PID>
   rm .stock_app.pid
   ```

### 服务状态异常

如果显示"进程不存在（PID文件残留）"：

```bash
# 清理PID文件并重新启动
python main.py stop
python main.py start
```

## 文件结构

```
stock-analysis-app/
├── main.py              # 主程序（守护进程管理）
├── .stock_app.pid      # PID文件（运行时自动生成）
├── logs/
│   └── app.log         # 服务日志文件
├── run_api.py          # API服务器启动脚本（独立使用）
└── run_web.py          # Web服务器启动脚本（独立使用）
```

## 高级用法

### 集成到系统服务

可以创建 systemd 服务文件实现开机自启动：

```ini
# /etc/systemd/system/stock-analysis.service
[Unit]
Description=股票分析系统
After=network.target

[Service]
Type=forking
User=aaronpan
WorkingDirectory=/data/home/aaronpan/stock-analysis-app
ExecStart=/usr/bin/python3 /data/home/aaronpan/stock-analysis-app/main.py start
ExecStop=/usr/bin/python3 /data/home/aaronpan/stock-analysis-app/main.py stop
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

使用方法：
```bash
sudo systemctl enable stock-analysis
sudo systemctl start stock-analysis
sudo systemctl status stock-analysis
sudo systemctl stop stock-analysis
```

### 监控日志

实时查看日志：
```bash
# 使用tail
tail -f logs/app.log

# 或使用less
less +F logs/app.log
```

### 进程管理

查看所有相关进程：
```bash
# 查看主进程
cat .stock_app.pid
ps -p $(cat .stock_app.pid)

# 查看所有子进程
pstree -p $(cat .stock_app.pid)
```

## 命令速查表

| 命令 | 说明 | 是否后台 |
|------|------|----------|
| `python main.py` | 启动所有服务 | ✅ 是 |
| `python main.py start` | 启动所有服务 | ✅ 是 |
| `python main.py start -f` | 启动所有服务 | ❌ 否 |
| `python main.py stop` | 停止服务 | - |
| `python main.py status` | 查看状态 | - |
| `python main.py restart` | 重启服务 | ✅ 是 |
| `python main.py --init-db` | 初始化数据库 | - |

## 常见问题

**Q: 为什么默认后台运行？**  
A: 生产环境通常需要服务在后台持续运行，不占用终端窗口。

**Q: 如何查看实时日志？**  
A: 使用 `tail -f logs/app.log` 或前台模式 `python main.py start --foreground`。

**Q: 服务崩溃了怎么办？**  
A: 查看 `logs/app.log` 了解原因，然后使用 `python main.py restart` 重启。

**Q: 可以同时运行多个实例吗？**  
A: 不可以，同一项目只能运行一个实例。不同项目可以在不同端口运行。

**Q: 如何修改端口？**  
A: 修改 `config.yaml` 中的 `api.port` 和 `web.port` 配置。

## 总结

新版本的 `main.py` 提供了完整的后台服务管理能力：

✅ 后台运行，不占用终端  
✅ 一键启动、停止、重启  
✅ 服务状态监控  
✅ 日志集中管理  
✅ 优雅停止机制  
✅ 兼容旧版本命令

让服务管理变得简单高效！
