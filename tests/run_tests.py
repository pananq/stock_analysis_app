#!/usr/bin/env python3
"""当前项目的稳定回归测试入口。"""

import argparse
import os
import sys
import unittest


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def build_suite() -> unittest.TestSuite:
    """加载无外部网络、无生产数据库依赖的维护中测试。"""
    from tests import test_new_features, test_surface_contracts

    suite = unittest.TestSuite()
    suite.addTests(
        unittest.defaultTestLoader.loadTestsFromModule(test_new_features)
    )
    suite.addTests(
        unittest.defaultTestLoader.loadTestsFromModule(test_surface_contracts)
    )
    return suite


def run_tests(verbosity: int = 2) -> unittest.TestResult:
    return unittest.TextTestRunner(verbosity=verbosity).run(build_suite())


def main() -> int:
    parser = argparse.ArgumentParser(description='股海罗盘回归测试')
    parser.add_argument(
        '--quick',
        action='store_true',
        help='兼容参数；当前默认测试集本身即为快速隔离测试',
    )
    parser.add_argument(
        '--module',
        choices=['features'],
        help='仅保留维护中的 features 测试模块',
    )
    args = parser.parse_args()
    result = run_tests(verbosity=2)
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main())
