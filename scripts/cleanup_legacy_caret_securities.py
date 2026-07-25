#!/usr/bin/env python3
"""清理旧版使用 ^ 前缀的港美指数目录及行情数据。

默认只输出检查结果；传入 --apply 才会删除。脚本只接受 HK/US 的
INDEX 记录，并在存在关注列表、策略结果或无前缀目标冲突时拒绝执行。
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, text

from app.utils import get_config
from app.utils.database_url import build_mysql_url


def inspect(connection):
    rows = connection.execute(text("""
        SELECT
            s.id, s.market, s.security_type, s.code, s.name,
            COUNT(DISTINCT d.trade_date) AS daily_rows,
            COUNT(DISTINCT w.id) AS watchlist_rows,
            COUNT(DISTINCT r.id) AS strategy_rows
        FROM stocks s
        LEFT JOIN daily_market d ON d.security_id = s.id
        LEFT JOIN watchlists w ON w.security_id = s.id
        LEFT JOIN strategy_results r ON r.security_id = s.id
        WHERE s.code LIKE '^%'
        GROUP BY s.id, s.market, s.security_type, s.code, s.name
        ORDER BY s.market, s.code
    """)).mappings().all()
    collisions = connection.execute(text("""
        SELECT old.id, old.market, old.code, target.id AS target_id
        FROM stocks old
        JOIN stocks target
          ON target.market = old.market
         AND target.security_type = old.security_type
         AND target.code = SUBSTRING(old.code, 2)
        WHERE old.code LIKE '^%'
    """)).mappings().all()
    return rows, collisions


def cleanup(apply=False):
    config = get_config()
    engine = create_engine(
        build_mysql_url(config.get('database.mysql')),
        pool_pre_ping=True,
    )
    with engine.connect() as connection:
        rows, collisions = inspect(connection)
        invalid = [
            row for row in rows
            if row['market'] not in {'HK', 'US'}
            or row['security_type'] != 'INDEX'
        ]
        referenced = [
            row for row in rows
            if row['watchlist_rows'] or row['strategy_rows']
        ]
        print(
            "legacy_securities=%s daily_rows=%s "
            "watchlist_rows=%s strategy_rows=%s collisions=%s"
            % (
                len(rows),
                sum(row['daily_rows'] for row in rows),
                sum(row['watchlist_rows'] for row in rows),
                sum(row['strategy_rows'] for row in rows),
                len(collisions),
            )
        )
        if invalid:
            raise RuntimeError(
                f"发现不属于 HK/US INDEX 的 ^ 代码，拒绝清理: {invalid}"
            )
        if referenced:
            raise RuntimeError(
                f"发现仍被用户或策略引用的 ^ 代码，拒绝清理: {referenced}"
            )
        if collisions:
            raise RuntimeError(
                f"发现无前缀目标冲突，拒绝清理: {collisions}"
            )
        if not apply:
            print("DRY_RUN：传入 --apply 才会执行删除")
            return
        if not rows:
            print("CLEANUP_OK deleted_securities=0 deleted_daily_rows=0")
            return

        ids = [int(row['id']) for row in rows]
        placeholders = ','.join(f':id_{index}' for index in range(len(ids)))
        params = {f'id_{index}': value for index, value in enumerate(ids)}
        daily_result = connection.execute(
            text(
                "DELETE FROM daily_market "
                f"WHERE security_id IN ({placeholders})"
            ),
            params,
        )
        stock_result = connection.execute(
            text(
                "DELETE FROM stocks "
                f"WHERE id IN ({placeholders})"
            ),
            params,
        )
        connection.commit()
        remaining = connection.execute(text(
            "SELECT COUNT(*) FROM stocks WHERE code LIKE '^%'"
        )).scalar_one()
        if remaining:
            raise RuntimeError(f"清理后仍有 {remaining} 条 ^ 证券")
        print(
            "CLEANUP_OK deleted_securities=%s deleted_daily_rows=%s"
            % (stock_result.rowcount, daily_result.rowcount)
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    cleanup(args.apply)


if __name__ == '__main__':
    main()
