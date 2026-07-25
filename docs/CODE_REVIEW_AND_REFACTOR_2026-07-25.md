# 代码 Review 与重构记录（2026-07-25）

## 本轮结论

项目的业务分层基本清晰，但原实现将数据库连接、A 股数据模型和页面行为耦合得较紧，
导致离线导入失败、测试依赖已删除的 SQLite/DuckDB 模块，也无法自然扩展到港美股。

本轮采用“保留现有 MySQL A 股链路、为跨市场读取增加独立适配层”的方式重构，避免要求
现有生产数据库立即迁移。

## 已完成

- 新增 CN/HK/US 市场与证券代码规范化，拒绝非法代码。
- 港美股日线数据支持 AkShare 东方财富、AkShare 新浪和 Yahoo Chart 顺序回退。
- 关注列表支持选择市场、查看一年日线、MA5/20/60 和基础风险分析。
- 新增可测试的技术分析服务，不依赖 AI 也能生成可解释结论。
- 新增 OpenAI-compatible AI 配置和日报综合解读。
- 新增 SMTP 邮件服务、日报预览/发送 API 和每日定时任务；支持全局收件人以及多用户独立
  收件人目标。
- AI 服务超时、限流或返回异常时，日报会降级为基础技术分析并继续投递。
- 手动发送日报只允许使用与当前用户明确匹配的收件人目标，避免多用户报告误投。
- 新增智能日报页面并统一导航、卡片、表格、响应式与状态视觉。
- 路由导入不再隐式连接 MySQL，快速测试可在无数据库环境运行。
- MCP 强制验证 API Token，连接结束时清理用户上下文，并恢复 DNS rebinding 防护。
- 系统配置、数据库状态和调度日志不再匿名公开。
- 移除默认 `admin/admin123`，初始管理员密码必须由环境变量显式注入且不会写入日志。
- 修复 `tools/clean_market_data.py` 中导致全仓无法编译的非 Python 占位符。
- 认证、关注列表和 API Token 服务支持注入数据库会话，并使用内存 SQLite 完成 API
  端到端测试，不改变生产 MySQL 路径。
- JWT 拒绝示例弱密钥，日志自动脱敏 URL 密码/Token，API 不再回传内部异常。
- 浏览器会话完全使用服务端 `HttpOnly`/`SameSite=Lax` Cookie，JWT 不再写入
  `localStorage`；HTML 页面与同源 Web API 均由服务端鉴权，外部 API 仍支持 Bearer Token。
- 调度器遵守总开关、各任务开关/时间与时区配置；停止脚本不再扫描误杀其他项目进程。
- 默认测试入口不再加载已经删除的 SQLite/DuckDB 模块。
- 旧版 SQLite/DuckDB 与真实外部服务测试已归档到 `tests/legacy/`；标准
  `unittest discover` 与项目测试入口现在运行同一套隔离回归。
- 新增 `python main.py doctor` 脱敏配置检查；认证密钥不合格时拒绝启动可访问服务。
- MySQL URL 改为结构化构造，支持密码中的特殊字符并确保连接日志隐藏密码。
- AI 请求只传递白名单技术指标，不外发用户可编辑的分组/备注文本，降低提示词注入风险。
- `main.py --init-db` 现在按 `ADMIN_INITIAL_PASSWORD` 创建缺失的初始管理员，已有管理员
  不会被重置；新密码统一要求 12-128 个字符。

## 配置原则

敏感信息只应放在项目目录的 `.env` 或部署平台密钥系统中。`config.yaml` 和 `.env`
均已加入忽略规则；已经进入 Git 历史的 Tushare Token 必须在供应商后台轮换，单纯删除
当前文件无法使历史密钥失效。

## 页面样式分析

- 原页面的信息层级主要依赖 Bootstrap 默认卡片，跨市场、分析状态和主要操作不够突出。
- 重构后统一深色导航、蓝色主色、页面 Hero、指标卡、市场标签、空状态与状态胶囊；
  关注列表把“查看日线”提升为主要操作，日报页按配置状态、AI 摘要和逐股分析分层。
- 导航在较窄桌面宽度下改为更晚展开，表格和日线弹窗保持响应式。
- 已对登录页、关注列表和智能日报进行浏览器视觉检查，并修复导航溢出和缺失模态框引起的
  JavaScript 控制台警告。

## 本地真实链路验证

- 已使用当前 `.env` 的 MySQL 连接成功创建 `stock_analysis` 数据库及全部数据表。
- 已通过真实 MySQL 会话验证注册数据写入、登录、HK/US 关注列表持久化、日报预览以及
  API Token 创建/撤销；验证结束后已清理临时用户、关注列表和 Token。
- 已通过实际网络拉取腾讯控股（HK `00700`）和 Apple（US `AAPL`）日线数据，
  AkShare 东方财富失败时能够自动回退到 AkShare 新浪。
- 当前 `.env` 的 `AUTH_SECRET_KEY` 已通过强度检查。
- 已使用当前配置的 DeepSeek OpenAI-compatible 服务完成真实最小请求；随后通过
  `tools/verify_live_ai_report.py` 创建隔离临时用户，真实拉取 HK/US 行情并生成 AI 日报。
  两只股票分析状态均为 `ok`，AI 摘要包含免责声明，临时 MySQL 记录已自动清理。

## 尚需外部服务验证

- 当前邮件功能未启用，SMTP 主机/发件人仍为示例配置且凭据为空；仍需使用实际 SMTP
  服务验证 TLS、发件人域名和反垃圾策略。配置后可运行
  `tools/verify_live_email.py --confirm-send` 显式发送验证邮件。
- 当前数据库没有用户；首次创建管理员还需在 `.env` 配置至少 12 字符的
  `ADMIN_INITIAL_PASSWORD`，再运行 `python main.py --init-db`。
- 当前 `api.cors_origins` 仍为 `*`；部署到非本机环境前应限制为实际 Web 来源。

## 测试命令

```bash
.venv/bin/python -m tests.run_tests
.venv/bin/python -m unittest discover -s tests -p "test*.py"
.venv/bin/python -m compileall -q app tests tools main.py
```

当前维护测试共 36 项，覆盖配置、认证安全、内存数据库 API 集成、CN/HK/US 标识、
港美股行情回退、技术分析、AI 请求、SMTP STARTTLS/认证/投递、邮件校验、日报编排、
MCP 鉴权和页面渲染。
