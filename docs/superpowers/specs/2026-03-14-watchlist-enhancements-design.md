# 股票列表添加关注 + 关注列表表格视图

## Context

用户提出两个 UI 改进需求：
1. 股票列表页搜索结果中，每行新增"加入关注"按钮，支持 Dropdown 选择分组
2. 关注列表页面改为表格视图（替代现有卡片视图），并显示股票名称、行业等完整信息

当前关注列表服务返回数据不含股票名称，只有 `stock_code`，需要补充。

---

## 改动范围

### 文件 1：`app/services/watchlist_service.py`

**目标**：`get_watchlist()` 返回的每条数据补充 `stock_name`、`industry`、`market_type`。

**方案**：仅修改 `get_watchlist()` 方法（不改 `_row_to_dict`，避免破坏 `add_stock`/`update_stock`/`get_item` 等其他调用方）。

在 `get_watchlist()` 的 `try` 块内（使用已有的 `session`），获取所有 watchlist 条目后，批量查询 `Stock` 表（`session.query(Stock).filter(Stock.code.in_(stock_codes))`），构建 `code → Stock` 的映射字典，再对每条 watchlist 记录调用 `_row_to_dict()` 后追加：
- `stock_name`（来自 `stocks.name`，查不到为 `None`）
- `industry`（来自 `stocks.industry`，查不到为 `None`）
- `market_type`（来自 `stocks.market_type`，查不到为 `None`）

注：使用 `get_watchlist()` 内已打开的 `self.Session()` session，无需新建连接。`Stock` 模型已在 `app/models/orm_models.py` 定义，直接 import 使用。

---

### 文件 2：`app/templates/stocks/index.html`

**目标**：在每行操作列新增"+ 关注" Dropdown 按钮。

**XSS 注意**：`escapeHtml()` 在 `watchlist.html` 中已有本地定义。`stocks/index.html` 中无此函数，需在 `{% block extra_js %}` 中本地定义相同的 `escapeHtml()` 函数（与 `watchlist.html` 中保持一致）。

**认证**：页面依赖现有 `checkAuth()`（已在 `base.html` 加载的 `common.js` 中自动执行，未登录直接跳转 `/login`）。`apiRequest()` 的 `.fail()` 回调已处理 401 自动跳转，无需额外处理。

**实现步骤**：

1. **页面初始化时**（`$(document).ready`），调用 `GET /watchlist`（无参数，获取全部条目）：
   - 提取所有 distinct `group_name`，存入 JS 变量 `existingGroups`（数组）
   - 提取所有 `stock_code` 存入 `watchedCodes`（Set），用于标记"已关注"状态
   - 调用 `updateWatchButtons()` 刷新所有行按钮状态

2. **操作列 HTML**（Jinja2 模板中渲染）：将原来单一的"查看详情"按钮改为 button group：
   ```html
   <div class="btn-group btn-group-sm">
     <a href="/stocks/{{ stock.code }}" class="btn btn-outline-primary">
       <i class="fas fa-eye"></i> 查看详情
     </a>
     <div class="btn-group btn-group-sm" role="group">
       <button type="button"
               class="btn btn-outline-warning btn-watch-toggle"
               data-stock-code="{{ stock.code }}"
               onclick="quickAddWatch('{{ stock.code }}')">
         <i class="fas fa-star"></i> 关注
       </button>
       <button type="button"
               class="btn btn-outline-warning dropdown-toggle dropdown-toggle-split btn-watch-dropdown"
               data-stock-code="{{ stock.code }}"
               data-bs-toggle="dropdown"
               data-bs-auto-close="outside">
       </button>
       <ul class="dropdown-menu watch-group-menu" data-stock-code="{{ stock.code }}">
         <li><a class="dropdown-item" href="#" onclick="addToWatchlist('{{ stock.code }}', null); return false;">
           <i class="fas fa-star"></i> 全部（不分组）</a></li>
         <li><hr class="dropdown-divider"></li>
         <!-- 已有分组动态插入 -->
         <li><hr class="dropdown-divider existing-groups-divider" style="display:none"></li>
         <li>
           <div class="px-3 py-1 new-group-input" style="display:none">
             <input type="text" class="form-control form-control-sm" placeholder="输入新分组名">
           </div>
           <a class="dropdown-item new-group-link" href="#" onclick="showNewGroupInput(this); return false;">
             <i class="fas fa-plus"></i> 新分组...</a>
         </li>
       </ul>
     </div>
   </div>
   ```

3. **`updateWatchButtons()`**：遍历所有 `.btn-watch-toggle[data-stock-code]`，若 code 在 `watchedCodes` 中则改为 `btn-success` + 文本"已关注" + disabled；否则保持"关注"可点击状态。

4. **`updateGroupDropdowns()`**：对每个 `.watch-group-menu`，在 "全部（不分组）" 和 "新分组" 之间插入 `existingGroups` 的菜单项（使用 `escapeHtml()` 转义分组名），显示 `.existing-groups-divider`。

5. **`quickAddWatch(stockCode)`**：主按钮点击，默认调用 `addToWatchlist(stockCode, null)`（不分组）。

6. **`addToWatchlist(stockCode, groupName)`**：
   - 调用 `apiRequest('/watchlist', 'POST', {stock_code: stockCode, market: 'CN', group_name: groupName}, callback)`
   - 成功后：`watchedCodes.add(stockCode)`，调用 `updateWatchButtons()`，`showMessage('已加入关注', 'success')`
   - 失败由 `apiRequest()` 内置 `.fail()` 回调自动显示服务器返回的 `error` 字段（无需额外处理 409）

7. **`showNewGroupInput(linkEl)`**：隐藏"新分组..."链接，显示同菜单项内的 input 框，按回车触发 `addToWatchlist(stockCode, inputValue)`，将**原始输入值（未转义）**追加到 `existingGroups`，再调用 `updateGroupDropdowns()` 刷新所有下拉菜单（`escapeHtml()` 仅在渲染 HTML 时调用，不在存储时调用）。

---

### 文件 3：`app/templates/watchlist.html`

**目标**：将卡片网格布局替换为 Bootstrap 表格视图。

**外层容器修改**：`#watchlist-container` 从 `<div class="row">` 改为一个 Bootstrap card + `table-responsive` 包裹（与股票列表风格一致）：
```html
<div class="card" id="watchlist-container">
  <div class="card-body p-0">
    <!-- table 动态插入 -->
  </div>
</div>
```

**表格列结构**：
| 股票代码 | 股票名称 | 行业 | 市场类型 | 分组 | 标签 | 备注 | 添加时间 | 操作 |

**修改 `renderWatchlist(items)`**：
- 空状态时在 `#watchlist-container` 内渲染原有空提示 div
- 有数据时渲染 `<div class="table-responsive"><table class="table table-hover mb-0">...</table></div>`
- `stock_code` 为可点击链接（`/stocks/<code>`），用 `escapeHtml()` 转义
- `stock_name`：显示 `item.stock_name || '-'`，用 `escapeHtml()` 转义
- `market_type`：Badge（沪市=`bg-primary`, 深市=`bg-success`, 北交所=`bg-warning`, 其他=`bg-secondary`），与股票列表一致
- `tags`：仍用 `<span class="badge bg-secondary">` 展示，用 `escapeHtml()` 转义
- 操作列保留编辑（`.btn-edit`）和删除（`.btn-delete`）按钮，data 属性不变

---

## 实现顺序

1. 修改 `watchlist_service.py`（补充股票元数据，仅改 `get_watchlist`）
2. 修改 `watchlist.html`（表格视图，依赖步骤 1 的新字段）
3. 修改 `stocks/index.html`（添加关注按钮，独立于步骤 1-2）

---

## 验证方案

1. 启动服务：`python main.py start --foreground`
2. 登录后进入「股票查询」页，搜索股票，确认：
   - 操作列出现"关注" Split Dropdown 按钮
   - 点击主按钮"关注"不分组添加成功，按钮变为"已关注"（绿色禁用）
   - 点击 Dropdown 箭头，显示"全部（不分组）"+ 已有分组 + "新分组..."
   - 选择已有分组成功关联分组
   - 点击"新分组..."显示输入框，回车后创建新分组并关联
   - 重复添加时 `apiRequest()` 自动展示"已在关注列表中"错误提示
3. 进入「关注列表」页，确认：
   - 股票以表格形式展示，包含代码、名称、行业、市场类型、分组等列
   - 分组过滤按钮仍然正常工作
   - 编辑和删除按钮正常工作
4. 运行测试：`python -m tests.run_tests --quick`
