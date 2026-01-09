# 需求文档

## 引言
当前股票行情数据更新过程中，stocks 表中的 `earliest_data_date` 和 `latest_data_date` 字段未被正确更新，导致这两个字段为 NULL。这使得每次增量更新行情数据时，系统无法确定数据范围，只能获取当日数据，可能遗漏历史数据或重复获取已存在的数据。

本功能旨在确保在每次更新行情数据（增量或全量）时，自动维护 stocks 表中的这两个日期字段，使其反映该股票在 daily_market 表中的实际数据范围。对于已有行情数据但 stocks 表日期字段为空的情况，需要进行初始化数据修复。

## 需求

### 需求 1：初始化修复已有数据的日期字段

**用户故事：** 作为一名数据管理员，我希望能够修复 stocks 表中已有行情数据但日期字段为空的情况，以便系统能够正确识别每只股票的数据范围。

#### 验收标准

1. WHEN 系统检测到 stocks 表中某股票的 earliest_data_date 和 latest_data_date 均为 NULL THEN 系统 SHALL 从 daily_market 表中查询该股票的 trade_date 字段
2. WHEN daily_market 表中存在该股票的行情数据 THEN 系统 SHALL 将最小 trade_date 设置为 earliest_data_date，最大 trade_date 设置为 latest_data_date
3. WHEN daily_market 表中不存在该股票的行情数据 THEN 系统 SHALL 保持这两个字段为 NULL
4. WHEN 初始化修复过程执行 THEN 系统 SHALL 记录修复的股票数量和详细信息到日志

### 需求 2：增量更新时维护日期字段

**用户故事：** 作为一名系统用户，我希望增量更新行情数据后，系统能够自动更新股票的数据日期范围，以便下次增量更新能够正确获取需要更新的数据。

#### 验收标准

1. WHEN 系统执行增量行情数据更新 THEN 系统 SHALL 在更新 daily_market 表后检查当前更新的数据日期
2. WHEN 更新的数据日期早于 stocks 表中现有的 earliest_data_date 或 earliest_data_date 为 NULL THEN 系统 SHALL 将 earliest_data_date 更新为较早的日期
3. WHEN 更新的数据日期晚于 stocks 表中现有的 latest_data_date 或 latest_data_date 为 NULL THEN 系统 SHALL 将 latest_data_date 更新为较晚的日期
4. WHEN 增量更新过程中出现错误 THEN 系统 SHALL 保持原有的 earliest_data_date 和 latest_data_date 不变

### 需求 3：全量更新时重新计算日期字段

**用户故事：** 作为一名数据管理员，我希望全量更新行情数据后，系统能够重新计算并更新股票的完整数据日期范围，以便确保日期字段的准确性。

#### 验收标准

1. WHEN 系统执行全量行情数据更新 THEN 系统 SHALL 在完成 daily_market 表更新后重新计算该股票的日期范围
2. WHEN 计算日期范围 THEN 系统 SHALL 从 daily_market 表中查询该股票的最小 trade_date 和最大 trade_date
3. WHEN 重新计算完成 THEN 系统 SHALL 将最小 trade_date 更新为 earliest_data_date，最大 trade_date 更新为 latest_data_date
4. WHEN 全量更新过程中出现错误 THEN 系统 SHALL 保持原有的 earliest_data_date 和 latest_data_date 不变

### 需求 4：新增股票时设置日期字段

**用户故事：** 作为一名系统用户，我希望新增股票并首次获取行情数据时，系统能够自动设置正确的数据日期范围，以便后续增量更新能够正常工作。

#### 验收标准

1. WHEN 系统为新增股票首次下载行情数据 THEN 系统 SHALL 在 daily_market 表插入数据后计算日期范围
2. WHEN 首次下载的数据插入成功 THEN 系统 SHALL 将最早日期设置为 earliest_data_date，最晚日期设置为 latest_data_date
3. WHEN 首次下载过程失败 THEN 系统 SHALL 保持 stocks 表中的这两个字段为 NULL

### 需求 5：日期字段更新的事务完整性

**用户故事：** 作为一名数据管理员，我希望日期字段的更新与行情数据的更新在同一事务中完成，以便确保数据的一致性。

#### 验收标准

1. WHEN 系统更新 daily_market 表 THEN 系统 SHALL 在同一数据库事务中更新 stocks 表的日期字段
2. WHEN 更新过程中发生任何错误 THEN 系统 SHALL 回滚所有更改，包括 daily_market 和 stocks 表的修改
3. WHEN 事务提交成功 THEN 系统 SHALL 确保 daily_market 和 stocks 表的更新都已生效

### 需求 6：日期字段更新的性能优化

**用户故事：** 作为一名系统用户，我希望批量更新行情数据时，日期字段的更新能够高效执行，以便不会显著影响整体更新性能。

#### 验收标准

1. WHEN 系统批量更新多只股票的行情数据 THEN 系统 SHALL 使用批量更新方式更新 stocks 表的日期字段
2. WHEN 批量更新日期字段 THEN 系统 SHALL 优先使用单条 SQL 语句更新多只股票，而非逐条更新
3. WHEN 批量更新超过 100 只股票 THEN 系统 SHALL 分批次更新，每批不超过 100 只
