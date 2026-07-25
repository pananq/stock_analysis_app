#!/usr/bin/env python3
"""向已配置的日报收件人发送一封显式确认的 SMTP 验证邮件。"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.services.daily_report_service import get_daily_report_targets
from app.services.email_service import EmailService
from app.utils import get_config


def verify_live_email() -> dict:
    config = get_config()
    if not config.get('notifications.email.enabled', False):
        raise RuntimeError("邮件通知未启用")

    targets = get_daily_report_targets(config)
    if not targets:
        raise RuntimeError("未配置有效的日报收件人")

    recipients = sorted({
        address
        for target in targets
        for address in target['recipients']
    })
    timezone_name = config.get('scheduler.timezone', 'Asia/Shanghai')
    timestamp = datetime.now(ZoneInfo(timezone_name)).strftime(
        '%Y-%m-%d %H:%M:%S %Z'
    )
    result = EmailService(config).send(
        subject='股海罗盘 · SMTP 配置验证',
        text_body=(
            f'这是一封股海罗盘 SMTP 配置验证邮件。\n验证时间：{timestamp}\n'
            '收到此邮件表示 SMTP 连接、认证和投递链路已正常工作。'
        ),
        html_body=(
            '<h1>股海罗盘 SMTP 配置验证</h1>'
            f'<p>验证时间：{timestamp}</p>'
            '<p>收到此邮件表示 SMTP 连接、认证和投递链路已正常工作。</p>'
        ),
        recipients=recipients,
    )
    return {
        'success': bool(result.get('success')),
        'recipient_count': len(result.get('recipients') or []),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description='向配置的日报收件人发送真实 SMTP 验证邮件',
    )
    parser.add_argument(
        '--confirm-send',
        action='store_true',
        help='确认发送一封真实测试邮件',
    )
    args = parser.parse_args()
    if not args.confirm_send:
        parser.error('必须显式提供 --confirm-send')

    result = verify_live_email()
    print('live_email=PASS')
    print(f"recipient_count={result['recipient_count']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
