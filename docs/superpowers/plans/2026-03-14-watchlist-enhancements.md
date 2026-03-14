# Watchlist Enhancements Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add "加入关注" dropdown button to stock list page and convert the watchlist page from card layout to table view with stock metadata.

**Architecture:** Three targeted changes — (1) enrich `get_watchlist()` response with stock name/industry/market_type via batch JOIN in the service layer; (2) update `watchlist.html` to render a Bootstrap table instead of cards; (3) add a split-button dropdown to each row of the stock list page that calls the watchlist API client-side.

**Tech Stack:** Python/Flask, SQLAlchemy 2.x, Bootstrap 5, jQuery, Jinja2

---

## File Map

| File | Change |
|------|--------|
| `app/services/watchlist_service.py` | Modify `get_watchlist()` to batch-query `Stock` table and append `stock_name`, `industry`, `market_type` to each result dict |
| `app/templates/watchlist.html` | Replace card grid with Bootstrap table in `renderWatchlist()`; update outer container HTML |
| `app/templates/stocks/index.html` | Add split-button dropdown to each row's action column; add init JS to load watched codes and groups |

---

## Chunk 1: Backend — enrich `get_watchlist()` with stock metadata

### Task 1: Modify `get_watchlist()` to include stock name, industry, market_type

**Files:**
- Modify: `app/services/watchlist_service.py` (line 138–149)

The current `get_watchlist()` only returns fields from the `watchlists` table. We need to JOIN the `stocks` table to get `name`, `industry`, `market_type` for display in the watchlist table view.

**Important:** Do NOT modify `_row_to_dict()` — it is used by `add_stock()`, `update_stock()`, and `get_item()` which do not have a `Stock` object available.

- [ ] **Step 1: Open the file and locate `get_watchlist()`**

  File: `app/services/watchlist_service.py`, lines 138–149.

  The current implementation:
  ```python
  def get_watchlist(self, user_id: int, group_name: str = None, tag: str = None) -> List[dict]:
      session = self.Session()
      try:
          query = session.query(Watchlist).filter(Watchlist.user_id == user_id)
          if group_name:
              query = query.filter(Watchlist.group_name == group_name)
          if tag:
              query = query.filter(Watchlist.tags.like(f'%,{tag},%'))
          items = query.order_by(Watchlist.created_at.desc()).all()
          return [self._row_to_dict(item) for item in items]
      finally:
          session.close()
  ```

- [ ] **Step 2: Update the import line to include `Stock`**

  Current import at line 8:
  ```python
  from app.models.orm_models import ORMDatabase, Watchlist
  ```
  Change to:
  ```python
  from app.models.orm_models import ORMDatabase, Watchlist, Stock
  ```

- [ ] **Step 3: Replace `get_watchlist()` with enriched version**

  Replace the entire method with:
  ```python
  def get_watchlist(self, user_id: int, group_name: str = None, tag: str = None) -> List[dict]:
      session = self.Session()
      try:
          query = session.query(Watchlist).filter(Watchlist.user_id == user_id)
          if group_name:
              query = query.filter(Watchlist.group_name == group_name)
          if tag:
              query = query.filter(Watchlist.tags.like(f'%,{tag},%'))
          items = query.order_by(Watchlist.created_at.desc()).all()

          # Batch-fetch stock metadata to avoid N+1 queries
          stock_codes = [item.stock_code for item in items]
          stock_map = {}
          if stock_codes:
              stocks = session.query(Stock).filter(Stock.code.in_(stock_codes)).all()
              stock_map = {s.code: s for s in stocks}

          result = []
          for item in items:
              d = self._row_to_dict(item)
              s = stock_map.get(item.stock_code)
              d['stock_name'] = s.name if s else None
              d['industry'] = s.industry if s else None
              d['market_type'] = s.market_type if s else None
              result.append(d)
          return result
      finally:
          session.close()
  ```

- [ ] **Step 4: Verify no syntax errors**

  Run:
  ```bash
  cd /data/home/aaronpan/stock-analysis-app
  python -c "from app.services.watchlist_service import WatchlistService; print('OK')"
  ```
  Expected: `OK`

- [ ] **Step 5: Run quick tests to confirm nothing broke**

  ```bash
  python -m tests.run_tests --quick
  ```
  Expected: all tests pass (watchlist service unit tests, if any, should pass)

- [ ] **Step 6: Commit**

  ```bash
  git add app/services/watchlist_service.py
  git commit -m "feat: enrich get_watchlist() with stock name, industry, market_type"
  ```

---

## Chunk 2: Frontend — watchlist table view

### Task 2: Replace card layout with table in `watchlist.html`

**Files:**
- Modify: `app/templates/watchlist.html`

The watchlist currently renders stocks as Bootstrap card grid (3 columns). Replace with a table matching the style of the stock list page (`stocks/index.html`).

The `#watchlist-container` `<div>` in the static HTML and the JS `renderWatchlist()` function both need updating.

- [ ] **Step 1: Update the `#watchlist-container` static HTML in the template**

  Locate lines 27–32 in `watchlist.html`:
  ```html
  <!-- Watchlist -->
  <div class="row" id="watchlist-container">
      <div class="col-12 text-center text-muted py-5" id="empty-hint">
          <i class="fas fa-star fa-3x mb-3"></i>
          <p>暂无关注股票，点击"添加股票"开始</p>
      </div>
  </div>
  ```

  Replace with:
  ```html
  <!-- Watchlist -->
  <div class="card" id="watchlist-container">
      <div class="card-body p-0">
          <div class="text-center text-muted py-5" id="empty-hint">
              <i class="fas fa-star fa-3x mb-3"></i>
              <p>暂无关注股票，点击"添加股票"开始</p>
          </div>
      </div>
  </div>
  ```

- [ ] **Step 2: Replace `renderWatchlist()` in the `{% block extra_js %}` section**

  Locate the existing `renderWatchlist(items)` function (lines 127–168) and replace it entirely with:

  ```javascript
  function marketTypeBadge(mt) {
      if (!mt) return '';
      const map = {'沪市': 'bg-primary', '深市': 'bg-success', '北交所': 'bg-warning'};
      const cls = map[mt] || 'bg-secondary';
      return '<span class="badge ' + cls + '">' + escapeHtml(mt) + '</span>';
  }

  function renderWatchlist(items) {
      const container = $('#watchlist-container .card-body');
      if (items.length === 0) {
          container.html('<div class="text-center text-muted py-5"><i class="fas fa-star fa-3x mb-3"></i><p>暂无关注股票</p></div>');
          return;
      }

      let rows = '';
      items.forEach(function(item) {
          const tags = item.tags ? item.tags.split(',').filter(t => t.trim()).map(t => '<span class="badge bg-secondary me-1">' + escapeHtml(t.trim()) + '</span>').join('') : '';
          rows += `<tr>
              <td><strong><a href="/stocks/${escapeHtml(item.stock_code)}" class="text-decoration-none">${escapeHtml(item.stock_code)}</a></strong></td>
              <td>${escapeHtml(item.stock_name || '-')}</td>
              <td>${escapeHtml(item.industry || '-')}</td>
              <td>${marketTypeBadge(item.market_type)}</td>
              <td>${item.group_name ? '<span class="badge bg-primary">' + escapeHtml(item.group_name) + '</span>' : '-'}</td>
              <td>${tags || '-'}</td>
              <td><small class="text-muted">${escapeHtml(item.notes || '-')}</small></td>
              <td><small class="text-muted">${item.created_at ? item.created_at.substring(0, 10) : '-'}</small></td>
              <td>
                  <button class="btn btn-sm btn-outline-secondary me-1 btn-edit"
                      data-id="${item.id}"
                      data-code="${escapeHtml(item.stock_code)}"
                      data-group="${escapeHtml(item.group_name || '')}"
                      data-tags="${escapeHtml(item.tags || '')}"
                      data-notes="${escapeHtml(item.notes || '')}">
                      <i class="fas fa-edit"></i>
                  </button>
                  <button class="btn btn-sm btn-outline-danger btn-delete" data-id="${item.id}">
                      <i class="fas fa-trash"></i>
                  </button>
              </td>
          </tr>`;
      });

      container.html(`
          <div class="table-responsive">
              <table class="table table-hover mb-0">
                  <thead>
                      <tr>
                          <th>股票代码</th>
                          <th>股票名称</th>
                          <th>行业</th>
                          <th>市场类型</th>
                          <th>分组</th>
                          <th>标签</th>
                          <th>备注</th>
                          <th>添加时间</th>
                          <th>操作</th>
                      </tr>
                  </thead>
                  <tbody>${rows}</tbody>
              </table>
          </div>
      `);
  }
  ```

- [ ] **Step 3: Verify page renders correctly in browser**

  Start the app (if not running):
  ```bash
  python main.py start --foreground
  ```
  Open `http://localhost:8000/watchlist` and confirm:
  - With no watchlist entries: empty-hint message visible inside the card
  - With entries: table renders with columns 股票代码, 股票名称, 行业, 市场类型, 分组, 标签, 备注, 添加时间, 操作
  - Edit and Delete buttons still work (click edit, modal opens with correct values; click delete, confirm prompt appears)
  - Group filter buttons above the table still filter correctly

- [ ] **Step 4: Run quick tests**

  ```bash
  python -m tests.run_tests --quick
  ```
  Expected: all tests pass

- [ ] **Step 5: Commit**

  ```bash
  git add app/templates/watchlist.html
  git commit -m "feat: replace watchlist card layout with table view showing stock metadata"
  ```

---

## Chunk 3: Frontend — "加入关注" button on stock list page

### Task 3: Add watchlist split-button dropdown to `stocks/index.html`

**Files:**
- Modify: `app/templates/stocks/index.html`

The stock list page is fully server-side rendered (Jinja2). Each row needs a client-side split button that: (a) quick-adds the stock with no group on main button click, (b) shows a dropdown with existing groups + "new group" input on arrow click.

The page initialises by fetching `GET /watchlist` (via `apiRequest()` from `common.js`) to populate `watchedCodes` and `existingGroups`.

**Authentication note:** `checkAuth()` in `common.js` already runs on page load and redirects unauthenticated users to `/login`. The `apiRequest()` `.fail()` handler auto-redirects on 401. No extra auth code is needed.

**XSS note:** `escapeHtml()` is NOT in `common.js` — it must be defined locally in this page's `{% block extra_js %}`.

- [ ] **Step 1: Update the action column in the Jinja2 table**

  Locate lines 147–151 in `stocks/index.html` (inside `{% for stock in stocks %}`):
  ```html
  <td>
      <a href="/stocks/{{ stock.code }}" class="btn btn-sm btn-outline-primary">
          <i class="fas fa-eye"></i> 查看详情
      </a>
  </td>
  ```

  Replace with:
  ```html
  <td>
      <div class="btn-group btn-group-sm">
          <a href="/stocks/{{ stock.code }}" class="btn btn-outline-primary">
              <i class="fas fa-eye"></i> 查看详情
          </a>
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
                  data-bs-auto-close="outside"
                  aria-expanded="false">
              <span class="visually-hidden">分组选项</span>
          </button>
          <ul class="dropdown-menu watch-group-menu" data-stock-code="{{ stock.code }}">
              <li>
                  <a class="dropdown-item" href="#"
                     onclick="addToWatchlist('{{ stock.code }}', null); return false;">
                      <i class="fas fa-star"></i> 全部（不分组）
                  </a>
              </li>
              <li><hr class="dropdown-divider"></li>
              {{/* existing groups injected here by JS */}}
              <li><hr class="dropdown-divider existing-groups-divider" style="display:none"></li>
              <li>
                  <div class="px-3 py-1 new-group-input" style="display:none">
                      <input type="text" class="form-control form-control-sm" placeholder="输入新分组名">
                  </div>
                  <a class="dropdown-item new-group-link" href="#"
                     onclick="showNewGroupInput(this); return false;">
                      <i class="fas fa-plus"></i> 新分组...
                  </a>
              </li>
          </ul>
      </div>
  </td>
  ```

  **Note:** Jinja2 comment syntax is `{# ... #}` not `{{/* ... */}}` — use `{# existing groups injected here by JS #}` if you want a comment there, or just leave no comment.

- [ ] **Step 2: Replace `{% block extra_js %}` with watchlist JS**

  The current `{% block extra_js %}` (lines 170–183) only contains `resetFilter()`. Replace it entirely with:

  ```html
  {% block extra_js %}
  <script>
  function escapeHtml(str) {
      if (!str) return '';
      return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
  }

  function resetFilter() {
      document.getElementById('code').value = '';
      document.getElementById('name').value = '';
      document.getElementById('industry').value = '';
      document.getElementById('market').value = '';
      document.getElementById('filterForm').submit();
  }

  let watchedCodes = new Set();
  let existingGroups = [];

  $(document).ready(function() {
      // Load watchlist to mark already-watched stocks and populate group lists
      apiRequest('/watchlist', 'GET', null, function(response) {
          const items = response.data || [];
          items.forEach(function(item) {
              watchedCodes.add(item.stock_code);
              if (item.group_name && !existingGroups.includes(item.group_name)) {
                  existingGroups.push(item.group_name);
              }
          });
          updateWatchButtons();
          updateGroupDropdowns();
      });
  });

  function updateWatchButtons() {
      $('.btn-watch-toggle').each(function() {
          const code = $(this).data('stock-code');
          if (watchedCodes.has(code)) {
              $(this)
                  .removeClass('btn-outline-warning')
                  .addClass('btn-success')
                  .prop('disabled', true)
                  .html('<i class="fas fa-check"></i> 已关注');
              // Also disable the dropdown split button
              $(this).next('.btn-watch-dropdown').prop('disabled', true);
          }
      });
  }

  function updateGroupDropdowns() {
      $('.watch-group-menu').each(function() {
          const menu = $(this);
          // Remove previously injected group items (avoid duplicates on re-render)
          menu.find('.injected-group').remove();
          const divider = menu.find('.existing-groups-divider');

          if (existingGroups.length > 0) {
              const stockCode = menu.data('stock-code');
              let groupHtml = '';
              existingGroups.forEach(function(g) {
                  // Use JSON.stringify so group names with ' or " don't break the JS string literal
                  const jsGroup = escapeHtml(JSON.stringify(g));
                  groupHtml += '<li class="injected-group"><a class="dropdown-item" href="#" onclick="addToWatchlist(\'' +
                      escapeHtml(stockCode) + '\', ' + jsGroup + '); return false;">' +
                      escapeHtml(g) + '</a></li>';
              });
              divider.before(groupHtml);
              divider.show();
          } else {
              divider.hide();
          }
      });
  }

  function quickAddWatch(stockCode) {
      addToWatchlist(stockCode, null);
  }

  function addToWatchlist(stockCode, groupName) {
      apiRequest('/watchlist', 'POST', {stock_code: stockCode, market: 'CN', group_name: groupName}, function(response) {
          watchedCodes.add(stockCode);
          if (groupName && !existingGroups.includes(groupName)) {
              existingGroups.push(groupName);
              updateGroupDropdowns();
          }
          updateWatchButtons();
          showMessage('已加入关注', 'success');
          // Close the open dropdown using Bootstrap's API to avoid stale visual state
          const openToggle = document.querySelector('.btn-watch-dropdown[aria-expanded="true"]');
          if (openToggle) {
              const dd = bootstrap.Dropdown.getInstance(openToggle);
              if (dd) dd.hide();
          }
      });
  }

  function showNewGroupInput(linkEl) {
      const li = $(linkEl).closest('li');
      const menu = $(linkEl).closest('.watch-group-menu');
      const stockCode = menu.data('stock-code');
      $(linkEl).hide();
      const inputDiv = li.find('.new-group-input');
      inputDiv.show();
      const input = inputDiv.find('input').val('').focus();

      input.off('keydown').on('keydown', function(e) {
          if (e.key === 'Enter') {
              const newGroup = $(this).val().trim();
              if (newGroup) {
                  addToWatchlist(stockCode, newGroup);
              }
              // Reset UI
              inputDiv.hide();
              $(linkEl).show();
          }
          if (e.key === 'Escape') {
              inputDiv.hide();
              $(linkEl).show();
          }
      });
  }
  </script>
  {% endblock %}
  ```

- [ ] **Step 3: Verify the button renders and works**

  With the app running, open `http://localhost:8000/stocks` and:
  1. Search for any stock — confirm each row now has a "关注" split button next to "查看详情"
  2. Click the main "关注" button — confirm success toast "已加入关注", button turns green "已关注"
  3. Click the dropdown arrow on another stock — confirm "全部（不分组）" appears, plus any existing groups
  4. Select a group from the dropdown — confirm success toast
  5. Click "新分组..." — confirm input field appears; type a name and press Enter — confirm success
  6. Refresh the page — already-watched stocks show "已关注" (green, disabled) immediately after page load

- [ ] **Step 4: Verify watchlist page still works**

  Open `http://localhost:8000/watchlist` — confirm newly added stocks appear in the table with name, industry, and market type populated.

- [ ] **Step 5: Run quick tests**

  ```bash
  python -m tests.run_tests --quick
  ```
  Expected: all tests pass

- [ ] **Step 6: Commit**

  ```bash
  git add app/templates/stocks/index.html
  git commit -m "feat: add watchlist split-button dropdown to stock list page"
  ```
