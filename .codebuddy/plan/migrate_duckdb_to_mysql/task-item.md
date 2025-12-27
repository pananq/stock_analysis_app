# 实施计划

- [ ] 1. 创建daily_market表的ORM模型
   - 在app/models/orm_models.py中定义DailyMarket类
   - 设置所有字段：code, trade_date, open, close, high, low, volume, amount, change_pct, turnover_rate, created_at
   - 配置联合主键(code, trade_date)
   - 创建索引：idx_daily_market_code, idx_daily_market_date, idx_daily_market_code_date
   - 设置InnoDB引擎和utf8mb4字符集
   - _需求：1.1, 1.2, 1.3, 1.4, 1.5_

- [ ] 2. 实现DuckDB到MySQL的数据迁移工具
   - 创建tools/migrate_duckdb_to_mysql.py迁移脚本
   - 实现批量读取DuckDB数据功能
   - 实现批量插入MySQL数据功能，使用ON DUPLICATE KEY UPDATE处理重复数据
   - 添加迁移统计功能：总记录数、成功插入数、跳过数、失败数、迁移耗时
   - 实现事务处理和错误回滚机制
   - 添加数据一致性验证功能：记录总数、股票数量、日期范围
   - 支持命令行参数：--dry-run模拟迁移
   - 实现进度显示和实时统计
   - 生成迁移报告并保存到日志文件
   - 在迁移前备份DuckDB数据文件
   - _需求：2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 7.1, 7.2, 7.3, 7.4, 8.1, 8.2, 8.3, 8.4_

- [ ] 3. 改造MarketDataService使用ORM访问MySQL
   - 修改app/services/market_data_service.py，移除DuckDBManager依赖
   - 改造import_all_history方法使用ORM保存数据到MySQL
   - 改造update_recent_data方法使用ORM查询、删除、插入数据
   - 改造get_stock_data方法使用ORM查询数据
   - 改造get_latest_data方法使用ORM查询最新数据
   - 改造get_data_date_range方法使用ORM查询日期范围
   - 改造get_statistics方法使用ORM查询统计信息
   - 确保所有方法返回数据格式保持不变
   - _需求：3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 10.1_

- [ ] 4. 改造清理工具使用ORM
   - 修改tools/clean_duckdb.py为tools/clean_market_data.py
   - 使用ORM方式清理MySQL中的历史行情数据
   - 保持原有的清理逻辑和参数
   - _需求：4.1_

- [ ] 5. 改造测试脚本使用ORM
   - 修改tests/test_market_data_service.py使用ORM访问MySQL
   - 修改tests/test_market_data_routes.py使用ORM访问MySQL
   - 修改performance_test.py使用ORM访问MySQL
   - 更新测试数据填充逻辑
   - 确保测试覆盖所有MarketDataService的方法
   - _需求：4.2, 4.3, 4.4_

- [ ] 6. 更新配置文件和依赖
   - 从config.py中移除database.duckdb_path配置项
   - 从.env文件中移除DuckDB相关配置
   - 从requirements.txt中移除duckdb包
   - _需求：6.1, 6.2, 5.6_

- [ ] 7. 清理DuckDB相关代码
   - 删除app/models/duckdb_manager.py文件
   - 从app/models/__init__.py中移除DuckDBManager和get_duckdb的导出
   - 删除tools/clean_duckdb.py文件
   - _需求：5.1, 5.2, 5.3_

- [ ] 8. 删除DuckDB数据库文件
   - 备份DuckDB数据库文件data/market_data.duckdb到data/market_data.duckdb.backup
   - 删除data/market_data.duckdb文件
   - _需求：5.4_

- [ ] 9. 更新系统文档
   - 更新README.md文档，移除DuckDB相关说明，添加MySQL存储说明
   - 创建数据库架构说明docs/database_schema.md，包含daily_market表的MySQL schema
   - 更新API文档反映数据存储方式的变化
   - _需求：5.5, 9.1, 9.2, 9.3, 9.4_

- [ ] 10. 验证和测试
   - 运行迁移工具执行数据迁移
   - 验证迁移后的数据完整性
   - 运行所有单元测试和集成测试
   - 运行性能测试，确保性能不显著下降
   - 测试API接口，确保数据格式和错误处理保持兼容
   - _需求：10.1, 10.2, 10.3_
