# 股海罗盘 MCP 服务使用指南

本文档说明如何将股海罗盘的 MCP 服务接入 Claude Desktop 或其他支持 MCP 协议的 AI 工具。

---

## 目录

1. [什么是 MCP 服务](#1-什么是-mcp-服务)
2. [前置条件](#2-前置条件)
3. [生成 API Token](#3-生成-api-token)
4. [配置 Claude Desktop](#4-配置-claude-desktop)
5. [可用工具说明](#5-可用工具说明)
6. [使用示例](#6-使用示例)
7. [故障排查](#7-故障排查)

---

## 1. 什么是 MCP 服务

MCP（Model Context Protocol）是 Anthropic 推出的开放协议，允许 AI 模型通过标准接口调用外部工具和数据源。

股海罗盘通过 MCP 服务（默认运行在 `:5002` 端口）对外暴露以下能力：

- **查询/管理关注列表**：让 Claude 直接读取你的股票关注清单
- **查询历史行情**：获取任意A股的 OHLCV 日线数据
- **查询技术指标**：获取移动均线（MA5/MA30/MA60 等）数据

配置完成后，你可以直接在 Claude 对话中提问，例如：
> "帮我看看我的关注列表里有哪些银行股，最近 30 天的走势怎么样？"

---

## 2. 前置条件

- 股海罗盘服务正在运行（API 服务 `:5000` + MCP 服务 `:5002`）
- 已有登录账号（用于生成 API Token）
- Claude Desktop 已安装（[下载地址](https://claude.ai/download)）

确认 MCP 服务正在运行：

```bash
curl http://your-server:5002/sse
# 应返回 SSE 连接头，不是 404
```

---

## 3. 生成 API Token

MCP 服务使用长期 API Token 认证（而非短期 JWT），Token 格式为 `sk-xxxxxxxx...`。

### 通过 Web 界面生成（推荐）

1. 登录 Web 界面：`http://your-server:8000`
2. 点击顶部导航栏 **「API Token」**
3. 点击 **「生成新 Token」**
4. 输入一个便于识别的名称，例如 `Claude Desktop`
5. 点击 **「生成」**
6. **立即复制明文 Token**（`sk-xxx...`）——关闭窗口后将无法再次查看

### 通过 API 生成

```bash
# 第一步：登录获取 JWT
JWT=$(curl -s -X POST http://your-server:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your-password"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

# 第二步：生成长期 API Token
curl -X POST http://your-server:5000/api/tokens \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"name":"Claude Desktop"}'

# 返回示例：
# {"success": true, "token": "sk-AbCdEfGh...", "prefix": "sk-AbCd", "id": 1}
```

> ⚠️ **Token 只返回一次**，请妥善保存。如果遗失，需撤销旧 Token 并重新生成。

---

## 4. 配置 Claude Desktop

### 4.1 找到配置文件

| 系统 | 配置文件路径 |
|------|-------------|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| Linux | `~/.config/Claude/claude_desktop_config.json` |

### 4.2 编辑配置

在配置文件中添加 `mcpServers` 配置：

```json
{
  "mcpServers": {
    "stock-analysis": {
      "url": "http://your-server:5002/sse",
      "headers": {
        "Authorization": "Bearer sk-你的Token"
      }
    }
  }
}
```

将 `your-server` 替换为实际服务器地址，`sk-你的Token` 替换为第 3 步生成的 Token。

**本机部署示例：**

```json
{
  "mcpServers": {
    "stock-analysis": {
      "url": "http://localhost:5002/sse",
      "headers": {
        "Authorization": "Bearer sk-AbCdEfGh..."
      }
    }
  }
}
```

### 4.3 重启 Claude Desktop

保存配置文件后，完全退出并重新启动 Claude Desktop。

### 4.4 验证连接

重启后，在 Claude 对话框中应能看到工具图标（锤子图标 🔨）。点击可查看已加载的工具列表，应包含 `get_watchlist`、`get_stock_data` 等。

---

## 5. 可用工具说明

### `get_watchlist` — 查询关注列表

获取当前账号的股票关注列表。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `group` | string | 否 | 按分组名过滤，如 `持仓`、`观察` |
| `tag` | string | 否 | 按标签过滤，如 `银行` |

返回示例：
```json
{
  "success": true,
  "count": 2,
  "data": [
    {
      "id": 1,
      "stock_code": "600000",
      "market": "CN",
      "group_name": "持仓",
      "tags": "银行,价值投资",
      "notes": "浦发银行，长期持有",
      "created_at": "2026-03-14 10:00:00"
    }
  ]
}
```

---

### `add_to_watchlist` — 添加股票到关注列表

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `stock_code` | string | **是** | 股票代码，如 `600000` |
| `market` | string | 否 | 市场，默认 `CN`（A股） |
| `group` | string | 否 | 分组名，如 `观察` |
| `tags` | string | 否 | 标签，逗号分隔，如 `银行,价值投资` |
| `notes` | string | 否 | 备注文字 |

---

### `remove_from_watchlist` — 从关注列表移除

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `watchlist_id` | int | **是** | 条目 ID（从 `get_watchlist` 结果中获取） |

---

### `get_stock_data` — 查询历史行情

获取股票日线 OHLCV 数据及期间统计。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `stock_code` | string | **是** | 股票代码，如 `600000` |
| `start_date` | string | 否 | 开始日期，格式 `YYYY-MM-DD` |
| `end_date` | string | 否 | 结束日期，格式 `YYYY-MM-DD` |
| `market` | string | 否 | 市场，默认 `CN` |

返回包含 `records`（逐日数据）和 `summary`（区间统计）：

```json
{
  "stock_code": "600000",
  "records": [
    {"date": "2026-03-14", "open": 10.5, "high": 10.8, "low": 10.4, "close": 10.7, "volume": 12345678}
  ],
  "summary": {
    "avg_price": 10.6,
    "max_price": 10.8,
    "min_price": 10.4,
    "total_days": 1
  }
}
```

---

### `get_stock_indicators` — 查询技术指标

获取移动均线（MA）数据。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `stock_code` | string | **是** | 股票代码，如 `600000` |
| `start_date` | string | 否 | 开始日期，格式 `YYYY-MM-DD` |
| `end_date` | string | 否 | 结束日期，格式 `YYYY-MM-DD` |
| `ma_periods` | string | 否 | 均线周期，逗号分隔，默认 `5,30,60` |

返回示例：
```json
{
  "stock_code": "600000",
  "indicators": {
    "MA5":  [{"date": "2026-03-14", "value": 10.62}],
    "MA30": [{"date": "2026-03-14", "value": 10.45}],
    "MA60": [{"date": "2026-03-14", "value": 10.31}]
  }
}
```

---

## 6. 使用示例

配置完成后，可以在 Claude 对话中直接提问：

**查看关注列表**
> 帮我列出我的所有关注股票

**按分组查询**
> 查询我"持仓"分组里的股票

**查看行情**
> 查一下 600000 最近一个月的收盘价走势

**查看均线**
> 帮我看看 000001 的 MA5 和 MA30，判断当前是否在均线上方

**综合分析**
> 我关注列表里有哪些银行股？帮我分别查一下近 60 天的行情，做个对比

---

## 7. 故障排查

### Claude Desktop 看不到工具

1. 确认配置文件 JSON 格式正确（可用 [jsonlint.com](https://jsonlint.com) 验证）
2. 确认 MCP 服务正在运行：`curl http://your-server:5002/sse`
3. 完全退出 Claude Desktop（macOS 需 Cmd+Q，不只是关窗口）后重启

### 工具调用返回"未认证"

Token 无效或已撤销。重新到 Web 界面生成新 Token，更新配置文件后重启 Claude Desktop。

### 行情数据为空

股票历史数据可能未导入。登录 Web 界面，进入「数据管理」→「全量导入历史数据」，或通过 API 触发导入：

```bash
curl -X POST http://your-server:5000/api/data/import \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"start_date":"2023-01-01"}'
```

### 确认 Token 有效性

```bash
# 通过 API 验证 Token 对应的用户
curl http://your-server:5000/api/tokens \
  -H "Authorization: Bearer $JWT"
```

若需测试 MCP Token 认证，也可以直接尝试发起 SSE 连接：

```bash
curl -H "Authorization: Bearer sk-你的Token" \
     http://your-server:5002/sse
```

---

*更多部署和运维说明请参见 [DEPLOYMENT.md](DEPLOYMENT.md)。*
