"""可配置的 OpenAI-compatible AI 分析客户端。"""

import json
from typing import Any, Dict, Iterable, Optional

import requests

from app.utils import get_config, get_logger


logger = get_logger(__name__)


class AIAnalysisService:
    ANALYSIS_FIELDS = (
        'stock_code',
        'market',
        'status',
        'as_of',
        'latest_close',
        'daily_change_pct',
        'period_high',
        'period_low',
        'annualized_volatility_pct',
        'risk_level',
        'signal',
        'moving_averages',
        'record_count',
        'summary',
    )

    def __init__(self, config=None, http_session=None):
        self.config = config or get_config()
        self.http = http_session or requests.Session()

    @property
    def enabled(self) -> bool:
        return bool(self.config.get('ai.enabled', False))

    def analyze_daily_report(
        self,
        analyses: Iterable[Dict[str, Any]],
    ) -> Optional[str]:
        if not self.enabled:
            return None

        api_key = self.config.get('ai.api_key')
        if not api_key:
            raise ValueError("AI 分析已启用，但未配置 AI_API_KEY")

        base_url = self.config.get('ai.base_url', 'https://api.openai.com/v1').rstrip('/')
        model = self.config.get('ai.model', 'gpt-4.1-mini')
        timeout = int(self.config.get('ai.timeout', 60))
        # 只向模型传递系统生成的技术字段，排除用户可编辑的分组、备注等文本，
        # 降低提示词注入和无关个人数据外发的风险。
        payload_data = [
            {
                key: item[key]
                for key in self.ANALYSIS_FIELDS
                if key in item
            }
            for item in analyses
        ]
        prompt = (
            "你是股票日报分析助手。请仅根据给定的历史技术指标生成简洁中文摘要，"
            "指出趋势、波动风险和需要关注的异常；不要承诺收益，不要虚构新闻或基本面。"
            "请使用简洁 Markdown：先写一段市场概览，再将每只证券写成独立的列表项，"
            "证券代码或名称使用粗体；最后以引用块写风险提示。"
            "结尾必须注明“不构成投资建议”。\n\n"
            f"数据：{json.dumps(payload_data, ensure_ascii=False)}"
        )
        response = self.http.post(
            f"{base_url}/chat/completions",
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
            json={
                'model': model,
                'temperature': 0.2,
                'messages': [
                    {'role': 'system', 'content': '你是严谨的市场数据分析助手。'},
                    {'role': 'user', 'content': prompt},
                ],
            },
            timeout=timeout,
        )
        response.raise_for_status()
        body = response.json()
        try:
            return body['choices'][0]['message']['content'].strip()
        except (KeyError, IndexError, TypeError, AttributeError) as exc:
            logger.error("AI 服务返回格式无效: %s", exc)
            raise ValueError("AI 服务返回格式无效") from exc
