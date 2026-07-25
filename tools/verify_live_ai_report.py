#!/usr/bin/env python3
"""验证真实港美股行情与 AI 日报，并自动清理临时数据库记录。"""

import argparse
import secrets
import string
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.models.database_factory import get_database
from app.models.orm_models import ApiToken, User, Watchlist
from app.services.auth_service import AuthService
from app.services.daily_report_service import DailyReportService
from app.services.watchlist_service import WatchlistService
from app.utils import get_config


def _temporary_username() -> str:
    suffix = ''.join(secrets.choice(string.ascii_lowercase) for _ in range(7))
    return f"codex{suffix}"


def verify_live_ai_report() -> dict:
    """创建隔离临时用户，验证真实行情和 AI，最终删除全部临时记录。"""
    config = get_config()
    if not config.get('ai.enabled', False):
        raise RuntimeError("AI 未启用")

    database = get_database()
    auth = AuthService(db=database)
    watchlist = WatchlistService()
    report_service = DailyReportService(
        watchlist_service=watchlist,
        config=config,
    )
    user_id = None

    try:
        username = _temporary_username()
        password = f"Live-{secrets.token_urlsafe(18)}"
        success, message, user = auth.register(username, password)
        if not success or not user:
            raise RuntimeError(f"创建临时用户失败: {message}")
        user_id = int(user['id'])

        for market, code in (('HK', '00700'), ('US', 'AAPL')):
            result = watchlist.add_stock(
                user_id=user_id,
                stock_code=code,
                market=market,
                group_name='live-verification',
            )
            if not result.get('success'):
                raise RuntimeError(f"添加 {market}:{code} 失败")

        report = report_service.build_report(user_id)
        if report.get('item_count') != 2:
            raise RuntimeError("日报未包含两只临时关注股票")
        if not report.get('ai_summary'):
            raise RuntimeError("AI 未返回日报摘要")

        return {
            'item_count': report['item_count'],
            'markets': sorted(
                item.get('market') for item in report['analyses']
            ),
            'statuses': [
                item.get('status') for item in report['analyses']
            ],
            'ai_summary_chars': len(report['ai_summary']),
            'has_disclaimer': '不构成投资建议' in report['ai_summary'],
        }
    finally:
        if user_id is not None:
            session = database.get_session()
            try:
                session.query(ApiToken).filter(
                    ApiToken.user_id == user_id
                ).delete()
                session.query(Watchlist).filter(
                    Watchlist.user_id == user_id
                ).delete()
                session.query(User).filter(User.id == user_id).delete()
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description='验证真实 HK/US 行情与已配置 AI 日报',
    )
    parser.add_argument(
        '--confirm-live',
        action='store_true',
        help='确认允许访问行情、AI 和项目配置的 MySQL',
    )
    args = parser.parse_args()
    if not args.confirm_live:
        parser.error('必须显式提供 --confirm-live')

    result = verify_live_ai_report()
    print('live_ai_report=PASS')
    for key, value in result.items():
        print(f'{key}={value}')
    print('temporary_mysql_data_cleanup=PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
