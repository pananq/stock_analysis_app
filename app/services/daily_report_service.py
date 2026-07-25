"""关注列表每日报告编排服务。"""

from datetime import date, datetime, timedelta
from html import escape
from typing import Optional
from zoneinfo import ZoneInfo

from app.services.ai_analysis_service import AIAnalysisService
from app.services.analysis_service import MarketAnalysisService
from app.services.email_service import EmailService
from app.utils import get_config, get_logger


logger = get_logger(__name__)


def get_daily_report_targets(
    config,
    include_profiles: bool = False,
    auth_service=None,
) -> list[dict]:
    """解析日报目标，并可用用户个人邮箱覆盖兼容配置。"""
    configured = config.get('notifications.daily_report.targets', []) or []
    targets = []
    for item in configured:
        if not isinstance(item, dict) or item.get('user_id') is None:
            continue
        recipients = item.get('recipients') or []
        if isinstance(recipients, str):
            recipients = [recipients]
        recipients = [
            str(address).strip() for address in recipients if str(address).strip()
        ]
        if recipients:
            try:
                user_id = int(item['user_id'])
            except (TypeError, ValueError):
                continue
            targets.append({
                'user_id': user_id,
                'recipients': recipients,
            })

    if not targets:
        recipients = config.get('notifications.email.recipients', []) or []
        if isinstance(recipients, str):
            recipients = [recipients]
        recipients = [
            str(address).strip() for address in recipients if str(address).strip()
        ]
        if recipients:
            try:
                user_id = int(
                    config.get('notifications.daily_report.user_id', 1)
                )
            except (TypeError, ValueError):
                user_id = None
            if user_id is not None:
                targets.append({
                    'user_id': user_id,
                    'recipients': recipients,
                })

    if not include_profiles:
        return targets

    if auth_service is None:
        from app.services.auth_service import AuthService
        auth_service = AuthService()
    try:
        personal_recipients = auth_service.list_report_recipients()
    except Exception:
        logger.exception("读取用户日报邮箱失败，继续使用系统收件人配置")
        return targets

    merged = {
        target['user_id']: target
        for target in targets
    }
    for item in personal_recipients:
        user_id = int(item['user_id'])
        # 用户个人开关拥有最终决定权；关闭时也会移除旧配置中的目标。
        merged.pop(user_id, None)
        email = str(item.get('email') or '').strip()
        if not item.get('enabled') or not email:
            continue
        merged[user_id] = {
            'user_id': user_id,
            'recipients': [email],
        }
    return [merged[user_id] for user_id in sorted(merged)]


class DailyReportService:
    def __init__(
        self,
        watchlist_service=None,
        analysis_service=None,
        ai_service=None,
        email_service=None,
        auth_service=None,
        config=None,
    ):
        self.config = config or get_config()
        if watchlist_service is None:
            from app.services.watchlist_service import get_watchlist_service
            watchlist_service = get_watchlist_service()
        self.watchlist = watchlist_service
        self.analysis = analysis_service or MarketAnalysisService()
        self.ai = ai_service or AIAnalysisService(self.config)
        self.email = email_service or EmailService(self.config)
        self.auth = auth_service

    def get_targets(self) -> list[dict]:
        """获取含用户个人邮箱的实际日报投递目标。"""
        return get_daily_report_targets(
            self.config,
            include_profiles=True,
            auth_service=self.auth,
        )

    def build_report(self, user_id: int, as_of: Optional[date] = None) -> dict:
        if as_of is None:
            timezone_name = self.config.get(
                'scheduler.timezone', 'Asia/Shanghai'
            )
            as_of = datetime.now(ZoneInfo(timezone_name)).date()
        lookback = int(self.config.get('notifications.daily_report.lookback_days', 90))
        start_date = (as_of - timedelta(days=lookback)).isoformat()
        end_date = as_of.isoformat()

        items = self.watchlist.get_watchlist(user_id)
        analyses = []
        for item in items:
            market = item.get('market', 'CN')
            security_type = item.get('security_type', 'STOCK')
            code = item['stock_code']
            try:
                data = self.watchlist.get_stock_dataframe(
                    code,
                    market=market,
                    security_type=security_type,
                    start_date=start_date,
                    end_date=end_date,
                )
                result = self.analysis.analyze(data, market, code)
            except Exception as exc:
                logger.exception("日报分析失败: %s:%s", market, code)
                result = {
                    'stock_code': code,
                    'market': market,
                    'status': 'error',
                    'summary': '行情读取或分析失败',
                }
            result['stock_name'] = item.get('stock_name')
            result['group_name'] = item.get('group_name')
            result['security_type'] = security_type
            analyses.append(result)

        ai_summary = None
        ai_error = None
        try:
            ai_summary = self.ai.analyze_daily_report(analyses)
        except Exception:
            # AI 是日报的增强能力，不应因供应商超时、限流或格式异常
            # 阻断基础技术分析和邮件投递。
            ai_error = 'AI 分析暂不可用，已生成基础技术分析'
            logger.exception("AI 日报摘要生成失败，已降级为基础技术分析")
        report = {
            'report_date': as_of.isoformat(),
            'user_id': user_id,
            'item_count': len(analyses),
            'analyses': analyses,
            'ai_enabled': self.ai.enabled,
            'ai_summary': ai_summary,
            'ai_error': ai_error,
        }
        report['text'] = self._render_text(report)
        report['html'] = self._render_html(report)
        return report

    def send_report(self, user_id: int, recipients=None) -> dict:
        report = self.build_report(user_id)
        if recipients is None:
            matching = next(
                (
                    target['recipients']
                    for target in self.get_targets()
                    if target['user_id'] == int(user_id)
                ),
                None,
            )
            if not matching:
                raise ValueError("当前用户未配置日报收件人")
            recipients = matching
        result = self.email.send(
            subject=f"股海罗盘关注列表日报 · {report['report_date']}",
            text_body=report['text'],
            html_body=report['html'],
            recipients=recipients,
        )
        return {'success': True, 'report': report, 'delivery': result}

    @staticmethod
    def _render_text(report: dict) -> str:
        lines = [
            f"股海罗盘关注列表日报 · {report['report_date']}",
            f"共分析 {report['item_count']} 只股票",
            '',
        ]
        if report.get('ai_summary'):
            lines.extend(['AI 摘要', report['ai_summary'], ''])
        for item in report['analyses']:
            label = item.get('stock_name') or item['stock_code']
            lines.append(
                f"[{item['market']}] {label} ({item['stock_code']}): "
                f"{item.get('summary', '-')}"
            )
        lines.extend(['', '仅基于历史行情分析，不构成投资建议。'])
        return '\n'.join(lines)

    @staticmethod
    def _render_html(report: dict) -> str:
        rows = []
        for item in report['analyses']:
            change = item.get('daily_change_pct')
            change_text = f"{change:+.2f}%" if isinstance(change, (int, float)) else '-'
            rows.append(
                '<tr>'
                f"<td>{escape(item['market'])}</td>"
                f"<td>{escape(item.get('stock_name') or item['stock_code'])}</td>"
                f"<td>{escape(item['stock_code'])}</td>"
                f"<td>{escape(str(item.get('latest_close', '-')))}</td>"
                f"<td>{escape(change_text)}</td>"
                f"<td>{escape(item.get('summary', '-'))}</td>"
                '</tr>'
            )
        ai_block = ''
        if report.get('ai_summary'):
            ai_block = (
                '<h2>AI 摘要</h2>'
                f"<p>{escape(report['ai_summary']).replace(chr(10), '<br>')}</p>"
            )
        return (
            '<!doctype html><html><body style="font-family:Arial,sans-serif;color:#172033">'
            f"<h1>股海罗盘关注列表日报 · {escape(report['report_date'])}</h1>"
            f"{ai_block}"
            '<table cellpadding="8" cellspacing="0" border="1" '
            'style="border-collapse:collapse;width:100%">'
            '<thead><tr><th>市场</th><th>股票</th><th>代码</th>'
            '<th>收盘价</th><th>日涨跌</th><th>分析</th></tr></thead>'
            f"<tbody>{''.join(rows)}</tbody></table>"
            '<p style="color:#697386">仅基于历史行情分析，不构成投资建议。</p>'
            '</body></html>'
        )


_daily_report_service = None


def get_daily_report_service() -> DailyReportService:
    global _daily_report_service
    if _daily_report_service is None:
        _daily_report_service = DailyReportService()
    return _daily_report_service
