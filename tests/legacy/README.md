# 历史测试归档

本目录保留旧版 SQLite/DuckDB 架构以及需要真实网络、真实 MySQL 数据的测试，
仅用于迁移时参考，不属于当前默认回归测试。

当前维护测试位于 `tests/test_new_features.py`，可以使用以下任一命令运行：

```bash
.venv/bin/python -m tests.run_tests
.venv/bin/python -m unittest discover -s tests -p "test*.py"
```

`legacy` 目录刻意不包含 `__init__.py`，避免标准测试发现误执行会修改真实数据
或访问外部服务的历史脚本。
