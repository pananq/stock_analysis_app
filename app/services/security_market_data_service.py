"""按市场与证券类型路由日线行情。"""

from datetime import datetime
from threading import Lock

import pandas as pd

from app.services.global_market_data_service import (
    get_global_market_data_service,
)
from app.services.market_data_service import get_market_data_service
from app.services.market_identity import (
    MARKETS,
    normalize_market,
    normalize_security_code,
    normalize_security_type,
)


class SecurityMarketDataService:
    """统一读取股票、ETF、基金和指数日线行情。"""

    def __init__(
        self,
        market_data_service=None,
        global_market_data_service=None,
        akshare_client=None,
    ):
        self.cn_stocks = market_data_service or get_market_data_service()
        self.global_markets = (
            global_market_data_service or get_global_market_data_service()
        )
        self.akshare = akshare_client

    def get_daily_data(
        self,
        code,
        market='CN',
        security_type='STOCK',
        start_date=None,
        end_date=None,
        limit=None,
    ):
        market = normalize_market(market)
        security_type = normalize_security_type(security_type)
        code = normalize_security_code(code, market, security_type)

        if security_type == 'STOCK':
            if market == 'CN':
                frame = self.cn_stocks.get_stock_data(
                    code=code,
                    start_date=start_date,
                    end_date=end_date,
                    limit=limit,
                )
            else:
                frame = self.global_markets.get_daily_data(
                    code,
                    market,
                    start_date=start_date,
                    end_date=end_date,
                )
        elif security_type in {'ETF', 'FUND'} and market == 'CN':
            frame = self._get_cn_fund_data(
                code,
                security_type,
                start_date,
                end_date,
            )
        elif security_type == 'INDEX' and market == 'CN':
            frame = self._get_cn_index_data(code, start_date, end_date)
        elif security_type == 'INDEX' and market == 'HK':
            frame = self._get_hk_index_data(code, start_date, end_date)
        elif security_type == 'INDEX' and market == 'US':
            frame = self.global_markets.get_daily_data(
                code,
                market,
                start_date=start_date,
                end_date=end_date,
                security_type=security_type,
            )
        else:
            # 港美 ETF、REIT 等使用与股票相同的交易所行情接口。
            frame = self.global_markets.get_daily_data(
                code,
                market,
                start_date=start_date,
                end_date=end_date,
                security_type=security_type,
            )

        frame = self._normalize_frame(
            frame,
            code,
            market,
            security_type,
        )
        return frame.tail(limit) if limit else frame

    def _get_cn_fund_data(
        self,
        code,
        security_type,
        start_date,
        end_date,
    ):
        ak = self._get_akshare()
        start = self._compact(start_date, '19900101')
        end = self._compact(end_date, datetime.now().strftime('%Y%m%d'))
        errors = []
        methods = (
            ('fund_etf_hist_em', {
                'symbol': code,
                'period': 'daily',
                'start_date': start,
                'end_date': end,
                'adjust': 'qfq',
            }),
            ('fund_lof_hist_em', {
                'symbol': code,
                'period': 'daily',
                'start_date': start,
                'end_date': end,
                'adjust': 'qfq',
            }),
            ('fund_etf_hist_sina', {
                'symbol': self._cn_exchange_symbol(code),
            }),
        )
        for method_name, kwargs in methods:
            if security_type == 'ETF' and method_name == 'fund_lof_hist_em':
                continue
            try:
                frame = getattr(ak, method_name)(**kwargs)
                if not frame.empty:
                    return self._filter_dates(frame, start_date, end_date)
            except Exception as exc:
                errors.append(f"{method_name}: {exc}")
        raise RuntimeError("无法获取基金日线；" + '；'.join(errors))

    def _get_cn_index_data(self, code, start_date, end_date):
        frame = self._get_akshare().stock_zh_index_daily(
            symbol=code.lower()
        )
        return self._filter_dates(frame, start_date, end_date)

    def _get_hk_index_data(self, code, start_date, end_date):
        frame = self._get_akshare().stock_hk_index_daily_sina(
            symbol=code.lstrip('^')
        )
        return self._filter_dates(frame, start_date, end_date)

    @staticmethod
    def _normalize_frame(
        frame,
        code,
        market,
        security_type,
    ):
        if frame is None or frame.empty:
            return pd.DataFrame()
        result = frame.copy()
        result = result.rename(columns={
            '日期': 'trade_date',
            'date': 'trade_date',
            '开盘': 'open',
            '收盘': 'close',
            '最高': 'high',
            '最低': 'low',
            '成交量': 'volume',
            '成交额': 'amount',
            '涨跌幅': 'change_pct',
        })
        required = ('trade_date', 'open', 'close', 'high', 'low')
        if any(column not in result for column in required):
            raise ValueError("行情数据缺少日期或 OHLC 字段")
        result['trade_date'] = pd.to_datetime(
            result['trade_date']
        ).dt.strftime('%Y-%m-%d')
        for column in (
            'open', 'close', 'high', 'low', 'volume',
            'amount', 'change_pct',
        ):
            if column in result:
                result[column] = pd.to_numeric(
                    result[column],
                    errors='coerce',
                )
        if 'change_pct' not in result:
            result['change_pct'] = result['close'].pct_change() * 100
        if 'volume' not in result:
            result['volume'] = None
        if 'amount' not in result:
            result['amount'] = None
        result['code'] = code
        result['market'] = market
        result['security_type'] = security_type
        result['currency'] = MARKETS[market].currency
        return (
            result[
                [
                    'code', 'market', 'security_type', 'currency',
                    'trade_date', 'open', 'close', 'high', 'low',
                    'volume', 'amount', 'change_pct',
                ]
            ]
            .dropna(subset=['trade_date', 'close'])
            .sort_values('trade_date')
            .reset_index(drop=True)
        )

    @staticmethod
    def _filter_dates(frame, start_date, end_date):
        if frame is None or frame.empty:
            return frame
        date_column = '日期' if '日期' in frame else 'date'
        if date_column not in frame:
            return frame
        dates = pd.to_datetime(frame[date_column])
        mask = pd.Series(True, index=frame.index)
        if start_date:
            mask &= dates >= pd.Timestamp(start_date)
        if end_date:
            mask &= dates <= pd.Timestamp(end_date)
        return frame.loc[mask].copy()

    @staticmethod
    def _compact(value, default):
        return str(value).replace('-', '') if value else default

    @staticmethod
    def _cn_exchange_symbol(code):
        return ('sh' if code.startswith(('5', '6')) else 'sz') + code

    def _get_akshare(self):
        if self.akshare is None:
            import akshare as ak

            self.akshare = ak
        return self.akshare


_security_market_data_service = None
_security_market_data_lock = Lock()


def get_security_market_data_service():
    global _security_market_data_service
    if _security_market_data_service is None:
        with _security_market_data_lock:
            if _security_market_data_service is None:
                _security_market_data_service = SecurityMarketDataService()
    return _security_market_data_service
