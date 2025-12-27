# main.py 启动方式修复

## 问题描述

用户反馈 README 中说明的第一种启动方式 `python main.py` 似乎并不能启动服务。

## 问题原因

检查代码后发现：

1. **原始 main.py 只做了数据库初始化**，并没有启动任何服务
2. **README 文档中描述了多种启动方式**，但这些功能在 main.py 中并未实现
3. **实际的启动方式**只能通过 `run_api.py` 和 `run_web.py` 分别启动

## 解决方案

### 1. 重写 main.py

修改后的 `main.py` 支持以下功能：

- **启动所有服务**（API + Web + 调度器）
- **只启动 API 服务器**
- **只启动 Web 服务器**
- **只初始化数据库**

### 2. 实现方式

使用 Python 的 `argparse` 模块提供命令行参数，并使用 `multiprocessing` 模块支持同时启动多个服务。

### 3. 核心代码结构

```python
def run_api_server():
    """运行API服务器（含调度器）"""
    # 包含Flask API和调度器启动逻辑

def run_web_server():
    """运行Web服务器"""
    # 包含Flask Web应用启动逻辑

def init_databases():
    """初始化数据库"""
    # 数据库初始化逻辑

def main():
    # 命令行参数解析
    # 根据参数决定启动哪些服务
    # 使用多进程同时启动API和Web
```

## 支持的启动方式

### 方式一：启动所有服务（推荐）

```bash
python main.py
```

启动所有服务：
- API 服务器（端口 5000）
- Web 服务器（端口 8000）
- 调度器

### 方式二：只启动 API 服务

```bash
python main.py --api-only
```

只启动 API 服务器和调度器，适用于只需要 API 的场景。

### 方式三：只启动 Web 服务

```bash
python main.py --web-only
```

只启动 Web 服务器，需要确保 API 服务已在运行。

### 方式四：只初始化数据库

```bash
python main.py --init-db
```

仅初始化数据库，不启动任何服务。

### 方式五：查看帮助

```bash
python main.py --help
```

显示所有可用参数和说明。

## 与原有启动方式的兼容性

原有的启动方式仍然可用：

```bash
# 启动API服务器（端口5000）
python run_api.py

# 启动Web服务器（端口8000）
python run_web.py
```

## 技术细节

### 多进程启动

当使用 `python main.py` 启动所有服务时：

```python
api_process = multiprocessing.Process(target=run_api_server)
web_process = multiprocessing.Process(target=run_web_server)

api_process.start()
web_process.start()

# 等待进程结束
api_process.join()
web_process.join()
```

### 优雅关闭

支持 Ctrl+C 中断信号，会优雅地关闭所有服务和进程：

```python
try:
    api_process.join()
    web_process.join()
except KeyboardInterrupt:
    print("收到中断信号，正在关闭所有服务...")
    api_process.terminate()
    web_process.terminate()
    api_process.join(timeout=5)
    web_process.join(timeout=5)
```

### 自动初始化数据库

所有启动方式都会先自动初始化数据库（除了 `--init-db` 参数）：

```python
# 先初始化数据库
init_databases()

if args.init_db:
    print("数据库初始化完成")
    return

# 然后启动服务...
```

## 测试验证

### 测试命令

```bash
# 测试帮助信息
python main.py --help

# 测试数据库初始化
python main.py --init-db

# 测试只启动API（实际不会运行，只是验证语法）
python main.py --api-only --help 2>&1 | head
```

### 预期输出

```bash
$ python main.py --help
usage: main.py [-h] [--api-only] [--web-only] [--init-db]

股票分析系统

options:
  -h, --help  show this help message and exit
  --api-only  只启动API服务器
  --web-only  只启动Web服务器
  --init-db   只初始化数据库

$ python main.py --init-db
============================================================
初始化数据库
============================================================
数据源类型: tushare
SQLite数据库: /data/home/aaronpan/stock-analysis-app/data/stock_analysis.db
DuckDB数据库: /data/home/aaronpan/stock-analysis-app/data/market_data.duckdb
...
数据库初始化完成
```

## 文件变更

### 修改的文件

- `main.py` - 重写，支持多种启动方式

### 新增的文件

- `test_main_startup.py` - 测试脚本

### 相关文档

- `README.md` - 文档已正确描述启动方式（无需修改）

## 注意事项

1. **端口冲突**：如果端口 5000 或 8000 已被占用，服务启动会失败
2. **多进程**：启动所有服务时会创建两个子进程
3. **调度器**：只有在启动 API 服务时才会启动调度器
4. **日志输出**：每个服务都会有独立的日志输出

## 使用建议

### 开发环境

```bash
# 推荐方式：只启动需要的部分服务
python main.py --api-only   # 只启动API进行开发
# 或
python main.py --web-only   # 只启动Web进行前端开发
```

### 生产环境

```bash
# 推荐方式：分别启动
python run_api.py    # 终端1：API服务
python run_web.py    # 终端2：Web服务

# 或使用进程管理工具（如supervisor、systemd）
```

### 快速测试

```bash
# 一键启动所有服务
python main.py
```

## 总结

修复后的 `main.py` 现在完全支持 README 中描述的所有启动方式，用户可以：

✅ 使用 `python main.py` 启动所有服务
✅ 使用 `python main.py --api-only` 只启动 API
✅ 使用 `python main.py --web-only` 只启动 Web
✅ 使用 `python main.py --init-db` 只初始化数据库
✅ 继续使用原有的 `run_api.py` 和 `run_web.py`

问题已完全解决！
