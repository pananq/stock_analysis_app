"""面向关注列表和日报的行情分析。"""

import math
from typing import Any, Dict

import pandas as pd


class MarketAnalysisService:
    """生成可解释、可测试的基础技术分析指标。"""

    def analyze(self, frame: pd.DataFrame, market: str, stock_code: str) -> Dict[str, Any]:
        if frame is None or frame.empty:
            return {
                'stock_code': stock_code,
                'market': market,
                'status': 'no_data',
                'summary': '暂无可用日线数据',
            }

        df = frame.copy().sort_values('trade_date')
        close = pd.to_numeric(df['close'], errors='coerce').dropna()
        if close.empty:
            return {
                'stock_code': stock_code,
                'market': market,
                'status': 'no_data',
                'summary': '暂无有效收盘价数据',
            }

        latest = float(close.iloc[-1])
        previous = float(close.iloc[-2]) if len(close) > 1 else latest
        daily_change = ((latest / previous) - 1) * 100 if previous else 0.0
        returns = close.pct_change().dropna()
        volatility = (
            float(returns.tail(20).std() * math.sqrt(252) * 100)
            if len(returns) > 1 else 0.0
        )

        moving_averages = {}
        for period in (5, 20, 60):
            if len(close) >= period:
                moving_averages[f'ma_{period}'] = round(
                    float(close.tail(period).mean()), 4
                )

        ma20 = moving_averages.get('ma_20')
        if ma20 is None:
            signal = 'insufficient_data'
            signal_text = '样本不足，暂不判断趋势'
        elif latest > ma20 * 1.02:
            signal = 'bullish'
            signal_text = '价格位于 20 日均线上方，短期趋势偏强'
        elif latest < ma20 * 0.98:
            signal = 'bearish'
            signal_text = '价格位于 20 日均线下方，短期趋势偏弱'
        else:
            signal = 'neutral'
            signal_text = '价格围绕 20 日均线震荡'

        risk = 'high' if volatility >= 45 else 'medium' if volatility >= 25 else 'low'
        return {
            'stock_code': stock_code,
            'market': market,
            'status': 'ok',
            'as_of': str(df.iloc[-1]['trade_date']),
            'latest_close': round(latest, 4),
            'daily_change_pct': round(daily_change, 2),
            'period_high': round(float(close.max()), 4),
            'period_low': round(float(close.min()), 4),
            'annualized_volatility_pct': round(volatility, 2),
            'risk_level': risk,
            'signal': signal,
            'moving_averages': moving_averages,
            'record_count': int(len(close)),
            'summary': signal_text,
            'disclaimer': '仅基于历史行情的技术分析，不构成投资建议。',
        }
