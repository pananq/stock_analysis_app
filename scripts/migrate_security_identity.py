#!/usr/bin/env python3
"""将证券身份从全局 code 迁移为 security_id。

生产执行示例：
    venv/bin/python scripts/migrate_security_identity.py --apply \
        --suffix 20260725_230000

脚本使用新表复制并校验数据，最后一次性 RENAME。旧表会保留为
`<table>_legacy_<suffix>`，便于快速回滚。
"""

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, text

from app.utils import get_config
from app.utils.database_url import build_mysql_url


TABLES = ('stocks', 'daily_market', 'watchlists', 'strategy_results')
STAGING = {
    'stocks': 'stocks_identity_new',
    'daily_market': 'daily_market_identity_new',
    'watchlists': 'watchlists_identity_new',
    'strategy_results': 'strategy_results_identity_new',
}


@dataclass
class Counts:
    stocks: int
    daily_market: int
    watchlists: int
    strategy_results: int


def scalar(connection, sql):
    return int(connection.execute(text(sql)).scalar_one())


def counts(connection, names=None):
    names = names or {table: table for table in TABLES}
    return Counts(**{
        table: scalar(connection, f"SELECT COUNT(*) FROM `{names[table]}`")
        for table in TABLES
    })


def execute_statements(connection, statements):
    for statement in statements:
        connection.execute(text(statement))


def create_statements(engine_name):
    suffix = (
        "DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
    )
    return [
        f"""
        CREATE TABLE `{STAGING['stocks']}` (
            id BIGINT NOT NULL AUTO_INCREMENT,
            code VARCHAR(20) NOT NULL,
            market VARCHAR(10) NOT NULL,
            name VARCHAR(500) NOT NULL,
            list_date DATE DEFAULT NULL,
            industry VARCHAR(200) DEFAULT NULL,
            market_type VARCHAR(50) DEFAULT NULL,
            security_type VARCHAR(20) NOT NULL DEFAULT 'STOCK',
            status VARCHAR(50) DEFAULT 'normal',
            earliest_data_date DATE DEFAULT NULL,
            latest_data_date DATE DEFAULT NULL,
            created_at DATETIME DEFAULT NULL,
            updated_at DATETIME DEFAULT NULL,
            PRIMARY KEY (id),
            UNIQUE KEY uq_stocks_market_code_type
                (market, code, security_type),
            KEY idx_stocks_code (code),
            KEY idx_stocks_market (market),
            KEY idx_status (status),
            KEY idx_industry (industry),
            KEY idx_market_type (market_type),
            KEY idx_security_type (security_type),
            KEY idx_earliest_data_date (earliest_data_date),
            KEY idx_latest_data_date (latest_data_date)
        ) ENGINE={engine_name} {suffix}
        """,
        f"""
        CREATE TABLE `{STAGING['daily_market']}` (
            security_id BIGINT NOT NULL,
            trade_date DATE NOT NULL,
            code VARCHAR(20) NOT NULL,
            open DECIMAL(10,2) DEFAULT NULL,
            close DECIMAL(10,2) DEFAULT NULL,
            high DECIMAL(10,2) DEFAULT NULL,
            low DECIMAL(10,2) DEFAULT NULL,
            volume BIGINT DEFAULT NULL,
            amount DECIMAL(20,2) DEFAULT NULL,
            change_pct DECIMAL(10,2) DEFAULT NULL,
            turnover_rate DECIMAL(10,2) DEFAULT NULL,
            created_at DATETIME DEFAULT NULL,
            PRIMARY KEY (security_id, trade_date),
            KEY idx_daily_market_code (code),
            KEY idx_daily_market_date (trade_date)
        ) ENGINE={engine_name} {suffix}
        """,
        f"""
        CREATE TABLE `{STAGING['watchlists']}` (
            id INT NOT NULL AUTO_INCREMENT,
            user_id INT NOT NULL,
            security_id BIGINT NOT NULL,
            stock_code VARCHAR(20) NOT NULL,
            market VARCHAR(20) NOT NULL,
            security_type VARCHAR(20) NOT NULL DEFAULT 'STOCK',
            group_name VARCHAR(100) DEFAULT NULL,
            tags VARCHAR(500) DEFAULT NULL,
            notes VARCHAR(500) DEFAULT NULL,
            created_at DATETIME DEFAULT NULL,
            PRIMARY KEY (id),
            UNIQUE KEY uq_watchlist_user_security (user_id, security_id),
            KEY idx_watchlist_security_id (security_id),
            KEY idx_watchlist_stock_code (stock_code),
            KEY idx_watchlist_group_name (group_name)
        ) ENGINE={engine_name} {suffix}
        """,
        f"""
        CREATE TABLE `{STAGING['strategy_results']}` (
            id INT NOT NULL AUTO_INCREMENT,
            strategy_id INT NOT NULL,
            security_id BIGINT DEFAULT NULL,
            stock_code VARCHAR(20) NOT NULL,
            trigger_date DATE NOT NULL,
            trigger_price FLOAT DEFAULT NULL,
            rise_percent FLOAT DEFAULT NULL,
            result_data TEXT DEFAULT NULL,
            executed_at DATETIME DEFAULT NULL,
            stock_name VARCHAR(100) DEFAULT NULL,
            trigger_pct_change DECIMAL(10,2) DEFAULT NULL,
            observation_days INT DEFAULT NULL,
            ma_period INT DEFAULT NULL,
            observation_result TEXT DEFAULT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            KEY idx_strategy_result_security_id (security_id),
            KEY idx_stock_code (stock_code),
            KEY idx_executed_at (executed_at),
            KEY idx_strategy_id (strategy_id),
            KEY idx_trigger_date (trigger_date)
        ) ENGINE={engine_name} {suffix}
        """,
    ]


def copy_stock_statement():
    return f"""
        INSERT INTO `{STAGING['stocks']}`
            (code, market, name, list_date, industry, market_type,
             security_type, status, earliest_data_date, latest_data_date,
             created_at, updated_at)
        SELECT
            code,
            CASE
                WHEN market_type IN ('HK', 'US') THEN market_type
                ELSE 'CN'
            END,
            name, list_date, industry, market_type,
            COALESCE(security_type, 'STOCK'),
            COALESCE(status, 'normal'),
            earliest_data_date, latest_data_date, created_at, updated_at
        FROM stocks
        ORDER BY code
    """


def copy_daily_market_in_batches(connection, batch_size):
    # 只转换 50-100 行的 stocks 批次一侧；转换 daily_market.code
    # 会让 MySQL/TDSQL 无法使用 439 万行旧表的主键索引。
    collated_stock_code = "s.code COLLATE utf8mb4_general_ci"
    max_id = scalar(
        connection,
        f"SELECT COALESCE(MAX(id), 0) FROM `{STAGING['stocks']}`",
    )
    copied = 0
    batch_number = 0
    for lower in range(0, max_id, batch_size):
        upper = lower + batch_size
        result = connection.execute(text(f"""
            INSERT INTO `{STAGING['daily_market']}`
            (security_id, trade_date, code, open, close, high, low,
             volume, amount, change_pct, turnover_rate, created_at)
            SELECT
            s.id, d.trade_date, d.code, d.open, d.close, d.high, d.low,
            d.volume, d.amount, d.change_pct, d.turnover_rate, d.created_at
            FROM `{STAGING['stocks']}` s
            JOIN daily_market d
              ON d.code = {collated_stock_code}
            WHERE s.id > :lower AND s.id <= :upper
        """), {'lower': lower, 'upper': upper})
        copied += result.rowcount
        batch_number += 1
        connection.commit()
        if batch_number % 20 == 0 or upper >= max_id:
            print(
                f"daily_market copied={copied} "
                f"security_id<={min(upper, max_id)}/{max_id}"
            )
    return copied


def copy_dependent_statements():
    return [
        f"""
        INSERT INTO `{STAGING['watchlists']}`
            (id, user_id, security_id, stock_code, market, security_type,
             group_name, tags, notes, created_at)
        SELECT
            w.id, w.user_id, s.id, w.stock_code, UPPER(w.market),
            COALESCE(w.security_type, 'STOCK'),
            w.group_name, w.tags, w.notes, w.created_at
        FROM watchlists w
        JOIN `{STAGING['stocks']}` s
          ON s.code = w.stock_code
         AND s.market = UPPER(w.market)
         AND s.security_type = COALESCE(w.security_type, 'STOCK')
        """,
        f"""
        INSERT INTO `{STAGING['strategy_results']}`
            (id, strategy_id, security_id, stock_code, trigger_date,
             trigger_price, rise_percent, result_data, executed_at,
             stock_name, trigger_pct_change, observation_days, ma_period,
             observation_result, created_at)
        SELECT
            r.id, r.strategy_id, s.id, r.stock_code, r.trigger_date,
            r.trigger_price, r.rise_percent, r.result_data, r.executed_at,
            r.stock_name, r.trigger_pct_change, r.observation_days,
            r.ma_period, r.observation_result, r.created_at
        FROM strategy_results r
        LEFT JOIN `{STAGING['stocks']}` s
          ON s.code = r.stock_code
        """,
    ]


def validate(connection, before):
    after = counts(connection, STAGING)
    if before != after:
        raise RuntimeError(f"迁移行数不一致: before={before}, after={after}")

    duplicate_identity = scalar(
        connection,
        f"""
        SELECT COUNT(*) FROM (
            SELECT market, code, security_type, COUNT(*) n
            FROM `{STAGING['stocks']}`
            GROUP BY market, code, security_type
            HAVING n > 1
        ) duplicated
        """,
    )
    if duplicate_identity:
        raise RuntimeError(f"发现 {duplicate_identity} 个重复证券身份")

    null_daily = scalar(
        connection,
        f"SELECT COUNT(*) FROM `{STAGING['daily_market']}` "
        "WHERE security_id IS NULL",
    )
    null_watchlists = scalar(
        connection,
        f"SELECT COUNT(*) FROM `{STAGING['watchlists']}` "
        "WHERE security_id IS NULL",
    )
    if null_daily or null_watchlists:
        raise RuntimeError(
            f"security_id 回填失败: daily={null_daily}, "
            f"watchlists={null_watchlists}"
        )
    return after


def migrate(apply, suffix, batch_size=100):
    config = get_config()
    mysql_config = config.get('database.mysql')
    engine = create_engine(build_mysql_url(mysql_config), pool_pre_ping=True)
    with engine.connect() as connection:
        existing = {
            row[0]
            for row in connection.execute(text("SHOW TABLES")).all()
        }
        staging_existing = set(STAGING.values()) & existing
        if staging_existing:
            raise RuntimeError(
                f"检测到未清理的迁移中间表: {sorted(staging_existing)}"
            )
        before = counts(connection)
        engine_name = connection.execute(text(
            "SELECT ENGINE FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'stocks'"
        )).scalar_one()
        print(f"engine={engine_name} before={before}")
        if not apply:
            print("DRY_RUN：结构检查通过；传入 --apply 才会执行迁移")
            return

        execute_statements(
            connection,
            create_statements(engine_name),
        )
        connection.commit()
        connection.execute(text(copy_stock_statement()))
        connection.commit()
        copied_daily = copy_daily_market_in_batches(
            connection,
            batch_size,
        )
        print(f"daily_market batch copy complete: {copied_daily}")
        execute_statements(connection, copy_dependent_statements())
        connection.commit()
        after = validate(connection, before)

        legacy = {
            table: f"{table}_legacy_{suffix}"
            for table in TABLES
        }
        collisions = set(legacy.values()) & existing
        if collisions:
            raise RuntimeError(
                f"旧表备份名称已存在: {sorted(collisions)}"
            )
        rename_pairs = []
        for table in TABLES:
            rename_pairs.extend([
                f"`{table}` TO `{legacy[table]}`",
                f"`{STAGING[table]}` TO `{table}`",
            ])
        connection.execute(text(
            "RENAME TABLE " + ", ".join(rename_pairs)
        ))
        connection.commit()
        print(f"MIGRATION_OK after={after}")
        print("legacy_tables=" + ",".join(legacy.values()))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    parser.add_argument(
        '--suffix',
        required=True,
        help='旧表后缀，仅允许数字和下划线',
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=100,
        help='每批复制的证券数量，默认 100',
    )
    args = parser.parse_args()
    if not re.fullmatch(r'[0-9_]+', args.suffix):
        raise SystemExit("--suffix 仅允许数字和下划线")
    if args.batch_size < 1 or args.batch_size > 1000:
        raise SystemExit("--batch-size 必须在 1-1000 之间")
    migrate(args.apply, args.suffix, args.batch_size)


if __name__ == '__main__':
    main()
