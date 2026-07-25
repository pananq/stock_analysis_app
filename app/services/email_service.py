"""SMTP 邮件发送服务。"""

import smtplib
import ssl
from email.message import EmailMessage
from typing import Iterable, Optional

from app.utils import get_config


class EmailService:
    def __init__(self, config=None, smtp_factory=None):
        self.config = config or get_config()
        self.smtp_factory = smtp_factory

    @property
    def enabled(self) -> bool:
        return bool(self.config.get('notifications.email.enabled', False))

    def send(
        self,
        subject: str,
        text_body: str,
        html_body: str,
        recipients: Optional[Iterable[str]] = None,
    ) -> dict:
        if not self.enabled:
            raise ValueError("邮件通知未启用")

        settings = self.config.get('notifications.email', {})
        recipients = [
            self._validate_address(address)
            for address in (recipients or settings.get('recipients') or [])
        ]
        if not recipients:
            raise ValueError("未配置日报收件人")

        message = EmailMessage()
        message['Subject'] = subject
        message['From'] = self._validate_address(settings.get('from_address'))
        message['To'] = ', '.join(recipients)
        message.set_content(text_body)
        message.add_alternative(html_body, subtype='html')

        host = settings.get('host')
        port = int(settings.get('port', 465 if settings.get('use_ssl') else 587))
        smtp_class = self.smtp_factory or (
            smtplib.SMTP_SSL if settings.get('use_ssl') else smtplib.SMTP
        )
        context = ssl.create_default_context()

        if settings.get('use_ssl'):
            client = smtp_class(host, port, timeout=30, context=context)
        else:
            client = smtp_class(host, port, timeout=30)

        with client:
            if settings.get('starttls') and not settings.get('use_ssl'):
                client.starttls(context=context)
            username = settings.get('username')
            password = settings.get('password')
            if username:
                client.login(username, password or '')
            client.send_message(message)
        return {'success': True, 'recipients': recipients}

    @staticmethod
    def _validate_address(address: str) -> str:
        normalized = str(address or '').strip()
        if (
            not normalized
            or '@' not in normalized
            or '\r' in normalized
            or '\n' in normalized
        ):
            raise ValueError("邮件地址格式无效")
        return normalized
