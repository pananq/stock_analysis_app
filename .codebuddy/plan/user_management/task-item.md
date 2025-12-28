# 实施计划

- [ ] 1. 数据库设计与迁移
   - 创建 `users` 表（包含 id, username, password_hash, role, created_at 等字段）
   - 修改 `strategies` 表，添加 `user_id` 外键字段
   - 修改 `job_logs` 表，添加 `user_id` 外键字段
   - 编写 SQL 迁移脚本，处理现有数据的归属（默认归属为管理员）
   - _需求：1.1, 4.2, 4.4_

- [ ] 2. 后端认证模块实现
   - 定义 User 数据模型与接口
   - 实现密码加密与验证工具函数
   - 创建 AuthService，实现注册、登录（生成 Token/Session）、注销逻辑
   - 实现 Auth 中间件，用于解析 Token 并注入当前用户信息到请求上下文
   - _需求：1.1, 1.3, 1.5_

- [ ] 3. 管理员工具与初始化
   - 实现系统启动检查，若无用户则自动创建默认管理员
   - 开发 CLI 脚本 `manage_admin.py`，支持重置管理员密码
   - _需求：2.1, 2.2, 2.3_

- [ ] 4. 业务逻辑权限改造
   - 更新 StrategyService，在 CRUD 操作中强制加入 `user_id` 过滤条件
   - 更新 JobService (任务调度)，在创建任务记录(`job_logs`)时记录 `user_id`
   - 更新 JobService，在查询任务列表时根据 `user_id` 过滤
   - 确保股票数据更新接口仅允许管理员角色调用
   - _需求：4.1, 4.2, 4.3, 4.4, 5.2, 5.3_

- [ ] 5. API 接口开发与更新
   - 新增 `/api/auth/login`, `/api/auth/register`, `/api/auth/logout`, `/api/auth/me` 接口
   - 更新 `/api/strategies` 相关接口，从 Auth 中间件获取 `user_id`
   - 更新 `/api/tasks` (job_logs) 相关接口，从 Auth 中间件获取 `user_id`
   - _需求：1.1, 4.1, 4.4_

- [ ] 6. 前端认证与基础架构
   - 创建登录与注册页面
   - 实现前端 Auth Store (Vuex/Pinia)，管理用户信息与登录状态
   - 配置路由守卫 (Router Guard)，未登录拦截跳转，非管理员拦截特定页面
   - _需求：1.3, 1.4, 3.1, 3.2_

- [ ] 7. 前端页面适配与功能集成
   - 更新仪表板、策略管理、任务列表页面，对接新的 API
   - 根据用户角色动态显示/隐藏“系统管理”、“数据更新”等入口
   - 测试普通用户与管理员的数据隔离效果
   - _需求：3.1, 3.3, 4.1, 5.1_
