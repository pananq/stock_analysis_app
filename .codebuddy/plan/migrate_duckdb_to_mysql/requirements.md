# 需求文档

## 引言

本项目当前使用DuckDB存储股票历史行情数据（日线行情），存储在`daily_market`表中。为了统一数据存储方案、简化架构并提高系统的可维护性，需要将历史行情数据从DuckDB迁移到MySQL数据库，并使用SQLAlchemy ORM模式进行数据访问。迁移完成后，需要删除DuckDB相关的所有代码和依赖。

本需求文档描述了数据迁移、ORM模型创建、服务层改造、测试适配以及DuckDB清理的完整流程。

---

## 需求

### 需求 1：创建历史行情数据的MySQL ORM模型

**用户故事：** 作为一名【系统开发者】，我希望【在ORM模型中定义历史行情数据的表结构】，以便【使用SQLAlchemy ORM方式统一访问所有数据】。

#### 验收标准

1. WHEN 【系统启动时】 THEN 【系统】 SHALL 【在MySQL数据库中自动创建daily_market表】

2. WHEN 【daily_market表被创建时】 THEN 【系统】 SHALL 【包含以下字段】：
   - code: VARCHAR(20), 股票代码
   - trade_date: DATE, 交易日期
   - open: DECIMAL(10, 2), 开盘价
   - close: DECIMAL(10, 2), 收盘价
   - high: DECIMAL(10, 2), 最高价
   - low: DECIMAL(10, 2), 最低价
   - volume: BIGINT, 成交量
   - amount: DECIMAL(20, 2), 成交额
   - change_pct: DECIMAL(10, 2), 涨跌幅
   - turnover_rate: DECIMAL(10, 2), 换手率
   - created_at: TIMESTAMP, 创建时间

3. WHEN 【daily_market表被创建时】 THEN 【系统】 SHALL 【设置联合主键(code, trade_date)】

4. WHEN 【daily_market表被创建时】 THEN 【系统】 SHALL 【创建以下索引】：
   - idx_daily_market_code: code字段
   - idx_daily_market_date: trade_date字段
   - idx_daily_market_code_date: (code, trade_date)联合索引

5. WHEN 【ORM模型创建时】 THEN 【系统】 SHALL 【使用InnoDB引擎和utf8mb4字符集】

---

### 需求 2：实现DuckDB到MySQL的数据迁移功能

**用户故事：** 作为一名【系统管理员】，我希望【将DuckDB中的所有历史行情数据完整迁移到MySQL】，以便【统一使用MySQL管理所有数据】。

#### 验收标准

1. WHEN 【执行数据迁移时】 THEN 【系统】 SHALL 【读取DuckDB中daily_market表的所有数据】

2. WHEN 【执行数据迁移时】 THEN 【系统】 SHALL 【支持批量插入数据到MySQL以提高性能】

3. WHEN 【执行数据迁移时】 THEN 【系统】 SHALL 【使用ON DUPLICATE KEY UPDATE处理重复数据】

4. WHEN 【数据迁移完成时】 THEN 【系统】 SHALL 【记录迁移的统计信息】：
   - 总记录数
   - 成功插入数
   - 跳过数（已存在）
   - 失败数
   - 迁移耗时

5. WHEN 【数据迁移失败时】 THEN 【系统】 SHALL 【记录详细的错误信息并回滚事务】

6. WHEN 【数据迁移完成后】 THEN 【系统】 SHALL 【验证MySQL和DuckDB的数据一致性】：
   - 记录总数相同
   - 股票数量相同
   - 日期范围相同

---

### 需求 3：改造MarketDataService使用ORM访问MySQL

**用户故事：** 作为一名【系统开发者】，我希望【MarketDataService使用ORM方式访问MySQL中的历史行情数据】，以便【统一使用ORM模式简化数据访问逻辑】。

#### 验收标准

1. WHEN 【MarketDataService初始化时】 THEN 【系统】 SHALL 【不再依赖DuckDBManager，而是使用ORMDatabase】

2. WHEN 【调用import_all_history方法时】 THEN 【系统】 SHALL 【使用ORM方式将行情数据保存到MySQL的daily_market表】

3. WHEN 【调用update_recent_data方法时】 THEN 【系统】 SHALL 【使用ORM方式查询、删除、插入MySQL中的行情数据】

4. WHEN 【调用get_stock_data方法时】 THEN 【系统】 SHALL 【使用ORM方式查询MySQL中的行情数据】

5. WHEN 【调用get_latest_data方法时】 THEN 【系统】 SHALL 【使用ORM方式查询MySQL中的最新行情数据】

6. WHEN 【调用get_data_date_range方法时】 THEN 【系统】 SHALL 【使用ORM方式查询MySQL中的日期范围】

7. WHEN 【调用get_statistics方法时】 THEN 【系统】 SHALL 【使用ORM方式查询MySQL中的统计信息】

---

### 需求 4：改造其他使用DuckDB的模块

**用户故事：** 作为一名【系统开发者】，我希望【所有使用DuckDB的模块都改为使用MySQL】，以便【完全移除DuckDB依赖】。

#### 验收标准

1. WHEN 【清理工具执行时】 THEN 【系统】 SHALL 【使用ORM方式清理MySQL中的历史行情数据】

2. WHEN 【测试脚本执行时】 THEN 【系统】 SHALL 【使用ORM方式填充MySQL测试数据】

3. WHEN 【集成测试运行时】 THEN 【系统】 SHALL 【使用ORM方式访问MySQL中的行情数据】

4. WHEN 【性能测试运行时】 THEN 【系统】 SHALL 【使用ORM方式访问MySQL中的行情数据】

---

### 需求 5：清理DuckDB相关代码和文件

**用户故事：** 作为一名【系统维护者】，我希望【删除所有DuckDB相关的代码和文件】，以便【简化系统架构并减少维护成本】。

#### 验收标准

1. WHEN 【迁移完成后】 THEN 【系统】 SHALL 【删除app/models/duckdb_manager.py文件】

2. WHEN 【迁移完成后】 THEN 【系统】 SHALL 【从app/models/__init__.py中移除DuckDBManager和get_duckdb的导出】

3. WHEN 【迁移完成后】 THEN 【系统】 SHALL 【删除tools/clean_duckdb.py文件】

4. WHEN 【迁移完成后】 THEN 【系统】 SHALL 【删除DuckDB数据库文件data/market_data.duckdb】

5. WHEN 【迁移完成后】 THEN 【系统】 SHALL 【更新README.md文档，移除DuckDB相关说明】

6. WHEN 【迁移完成后】 THEN 【系统】 SHALL 【从依赖文件requirements.txt中移除duckdb包】

---

### 需求 6：更新配置文件

**用户故事：** 作为一名【系统管理员】，我希望【配置文件中移除DuckDB相关配置】，以便【配置文件更加简洁】。

#### 验收标准

1. WHEN 【系统启动时】 THEN 【系统】 SHALL 【不再需要读取database.duckdb_path配置项】

2. WHEN 【配置文件被更新时】 THEN 【系统】 SHALL 【移除DuckDB相关的配置项】

---

### 需求 7：提供数据迁移工具

**用户故事：** 作为一名【系统管理员】，我希望【有一个独立的迁移工具】，以便【方便地执行数据迁移操作】。

#### 验收标准

1. WHEN 【运行迁移工具时】 THEN 【系统】 SHALL 【提供命令行接口执行迁移】

2. WHEN 【运行迁移工具时】 THEN 【系统】 SHALL 【显示迁移进度和实时统计信息】

3. WHEN 【迁移工具完成时】 THEN 【系统】 SHALL 【生成迁移报告并保存到日志文件】

4. WHEN 【迁移工具执行时】 THEN 【系统】 SHALL 【支持--dry-run参数进行模拟迁移】

---

### 需求 8：保证数据完整性和一致性

**用户故事：** 作为一名【系统管理员】，我希望【迁移过程中的数据完整性和一致性得到保证】，以便【不影响业务的正常运行】。

#### 验收标准

1. WHEN 【数据迁移过程中】 THEN 【系统】 SHALL 【使用数据库事务确保原子性】

2. WHEN 【数据迁移完成后】 THEN 【系统】 SHALL 【提供数据验证功能对比DuckDB和MySQL的数据】

3. WHEN 【迁移工具执行时】 THEN 【系统】 SHALL 【在迁移前备份DuckDB数据文件】

4. WHEN 【迁移失败时】 THEN 【系统】 SHALL 【保留DuckDB数据文件以便恢复】

---

### 需求 9：更新系统文档

**用户故事：** 作为一名【系统开发者】，我希望【系统文档反映最新的数据存储架构】，以便【新开发者能够快速理解系统结构】。

#### 验收标准

1. WHEN 【文档更新时】 THEN 【系统】 SHALL 【更新数据库架构说明文档】

2. WHEN 【文档更新时】 THEN 【系统】 SHALL 【添加daily_market表的MySQL schema说明】

3. WHEN 【文档更新时】 THEN 【系统】 SHALL 【移除DuckDB相关的文档】

4. WHEN 【文档更新时】 THEN 【系统】 SHALL 【更新API文档反映数据存储方式的变化】

---

### 需求 10：保持向后兼容性

**用户故事：** 作为一名【API使用者】，我希望【迁移前后的API接口保持兼容】，以便【不需要修改调用方代码】。

#### 验收标准

1. WHEN 【API接口被调用时】 THEN 【系统】 SHALL 【返回数据格式保持不变】

2. WHEN 【API接口被调用时】 THEN 【系统】 SHALL 【错误处理机制保持不变】

3. WHEN 【API接口被调用时】 THEN 【系统】 SHALL 【性能不出现显著下降】
