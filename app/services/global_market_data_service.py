"""港股和美股日线行情服务。"""

from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Optional
import time

import pandas as pd
import requests

from app.services.market_identity import MARKETS, normalize_market, normalize_security_code
from app.utils import get_config, get_logger


logger = get_logger(__name__)


class GlobalMarketDataService:
    """通过 AkShare 获取并标准化港股、美股日线行情。"""

    STANDARD_COLUMNS = [
        'code', 'market', 'currency', 'trade_date', 'open', 'close',
        'high', 'low', 'volume', 'amount', 'change_pct', 'source',
    ]

    def __init__(self, ak_client=None, config=None, http_session=None):
        self.config = config or get_config()
        if ak_client is None:
            import akshare as ak
            ak_client = ak
        self.ak = ak_client
        self.http = http_session or requests.Session()
        self._us_symbol_cache = {}
        self._data_cache = OrderedDict()
        self._cache_lock = Lock()
        # AkShare 的部分美股接口内部使用嵌入式 JavaScript 引擎，
        # 同一进程并发调用时可能直接导致解释器崩溃。串行化上游读取，
        # 并在获得锁后再次检查缓存，让并发的行情/分析请求只抓取一次。
        self._provider_lock = Lock()

    def get_daily_data(
        self,
        stock_code: str,
        market: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        adjust: Optional[str] = None,
        security_type: Optional[str] = None,
    ) -> pd.DataFrame:
        market = normalize_market(market)
        if market == 'CN':
            raise ValueError("GlobalMarketDataService 仅处理 HK/US 市场")

        effective_type = (
            security_type
            or ('INDEX' if str(stock_code).strip().startswith('^') else 'STOCK')
        )
        code = normalize_security_code(
            stock_code,
            market,
            effective_type,
        )
        start = self._compact_date(start_date or self._default_start_date())
        end = self._compact_date(end_date or datetime.now().strftime('%Y-%m-%d'))
        if start > end:
            raise ValueError("start_date 不能晚于 end_date")
        adjust = adjust if adjust is not None else self.config.get(
            'global_markets.adjust', 'qfq'
        )
        cache_key = (market, effective_type, code, start, end, adjust)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        with self._provider_lock:
            cached = self._get_cached(cache_key)
            if cached is not None:
                return cached
            return self._load_daily_data(
                code=code,
                market=market,
                start=start,
                end=end,
                start_date=start_date,
                end_date=end_date,
                adjust=adjust,
                cache_key=cache_key,
                security_type=effective_type,
            )

    def _load_daily_data(
        self,
        code,
        market,
        start,
        end,
        start_date,
        end_date,
        adjust,
        cache_key,
        security_type,
    ):
        providers = self.config.get(
            'global_markets.providers',
            ['akshare', 'akshare_sina', 'tencent', 'yahoo'],
        )
        if isinstance(providers, str):
            providers = [providers]
        else:
            providers = list(providers)
        if security_type == 'INDEX' and 'tencent' in providers:
            providers = [
                'tencent',
                *[provider for provider in providers if provider != 'tencent'],
            ]

        errors = []
        for provider in providers:
            try:
                if provider == 'akshare':
                    result = self._get_akshare_data(
                        code, market, start, end, adjust
                    )
                elif provider == 'akshare_sina':
                    result = self._get_akshare_sina_data(
                        code, market, start, end, adjust
                    )
                elif provider == 'tencent':
                    result = self._get_tencent_data(
                        code, market, start, end
                    )
                elif provider == 'yahoo':
                    result = self._get_yahoo_data(
                        code,
                        market,
                        start_date,
                        end_date,
                        security_type=security_type,
                    )
                else:
                    raise ValueError(f"未知的全球行情数据源: {provider}")
                if not result.empty:
                    self._set_cached(cache_key, result)
                    return result.copy(deep=True)
            except Exception as exc:
                errors.append(f"{provider}: {exc}")
                logger.warning(
                    "全球行情数据源 %s 获取 %s:%s 失败: %s",
                    provider, market, code, exc,
                )
        raise RuntimeError(
            f"无法获取 {market}:{code} 日线行情；" + '；'.join(errors)
        )

    def _get_cached(self, key) -> Optional[pd.DataFrame]:
        ttl = int(self.config.get('global_markets.cache_ttl', 300))
        if ttl <= 0:
            return None
        now = time.monotonic()
        with self._cache_lock:
            entry = self._data_cache.get(key)
            if entry is None:
                return None
            created_at, frame = entry
            if now - created_at > ttl:
                self._data_cache.pop(key, None)
                return None
            self._data_cache.move_to_end(key)
            return frame.copy(deep=True)

    def _set_cached(self, key, frame: pd.DataFrame):
        max_entries = int(
            self.config.get('global_markets.cache_max_entries', 256)
        )
        if max_entries <= 0:
            return
        with self._cache_lock:
            self._data_cache[key] = (time.monotonic(), frame.copy(deep=True))
            self._data_cache.move_to_end(key)
            while len(self._data_cache) > max_entries:
                self._data_cache.popitem(last=False)

    def _get_akshare_data(
        self, code: str, market: str, start: str, end: str, adjust: str
    ) -> pd.DataFrame:
        if market == 'HK':
            raw = self.ak.stock_hk_hist(
                symbol=code,
                period='daily',
                start_date=start,
                end_date=end,
                adjust=adjust,
            )
        else:
            symbol = self._resolve_us_symbol(code)
            raw = self.ak.stock_us_hist(
                symbol=symbol,
                period='daily',
                start_date=start,
                end_date=end,
                adjust=adjust,
            )
        return self._normalize_frame(raw, code, market, 'akshare')

    def _get_akshare_sina_data(
        self, code: str, market: str, start: str, end: str, adjust: str
    ) -> pd.DataFrame:
        if market == 'HK':
            raw = self.ak.stock_hk_daily(symbol=code, adjust=adjust)
        else:
            raw = self.ak.stock_us_daily(
                symbol=code.split('.', 1)[-1] if code[:3].isdigit() else code,
                adjust=adjust,
            )
        result = self._normalize_frame(raw, code, market, 'akshare_sina')
        start_iso = datetime.strptime(start, '%Y%m%d').strftime('%Y-%m-%d')
        end_iso = datetime.strptime(end, '%Y%m%d').strftime('%Y-%m-%d')
        return result[
            (result['trade_date'] >= start_iso) & (result['trade_date'] <= end_iso)
        ].reset_index(drop=True)

    def _get_yahoo_data(
        self,
        code: str,
        market: str,
        start_date: Optional[str],
        end_date: Optional[str],
        security_type: Optional[str] = None,
    ) -> pd.DataFrame:
        symbol = self._yahoo_symbol(code, market, security_type)
        start = self._unix_time(start_date or self._default_start_date())
        # Yahoo 的 period2 是开区间，因此向后增加一天。
        effective_end = end_date or datetime.now().strftime('%Y-%m-%d')
        period2 = self._unix_time(
            (datetime.strptime(effective_end, '%Y-%m-%d') + timedelta(days=1))
            .strftime('%Y-%m-%d')
        )
        timeout = int(self.config.get('global_markets.request_timeout', 30))
        response = self.http.get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
            params={
                'period1': start,
                'period2': period2,
                'interval': '1d',
                'events': 'div,splits',
                'includeAdjustedClose': 'true',
            },
            headers={'User-Agent': 'Mozilla/5.0 stock-analysis-app/2.0'},
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
        chart = payload.get('chart', {})
        if chart.get('error'):
            raise LookupError(chart['error'].get('description') or str(chart['error']))
        results = chart.get('result') or []
        if not results:
            return pd.DataFrame(columns=self.STANDARD_COLUMNS)
        result = results[0]
        quote = (result.get('indicators', {}).get('quote') or [{}])[0]
        timestamps = result.get('timestamp') or []
        raw = pd.DataFrame({
            'trade_date': [
                datetime.fromtimestamp(value, tz=timezone.utc).date()
                for value in timestamps
            ],
            'open': quote.get('open', []),
            'close': quote.get('close', []),
            'high': quote.get('high', []),
            'low': quote.get('low', []),
            'volume': quote.get('volume', []),
        })
        return self._normalize_frame(raw, code, market, 'yahoo')

    def _get_tencent_data(
        self,
        code: str,
        market: str,
        start: str,
        end: str,
    ) -> pd.DataFrame:
        """从腾讯行情接口读取港美日线，作为海外接口受限时的回退。"""
        symbol = self._tencent_symbol(code, market)
        payload, item = self._request_tencent_history(
            symbol, start, end
        )
        rows = item.get('day') or item.get('qfqday') or []

        # 美股历史接口需要交易所后缀（如 AAPL.OQ、A.N）。首次
        # 查询即使没有 day，qt 中仍会返回标准代码，可据此重试。
        if market == 'US':
            quote_groups = item.get('qt') or {}
            quote = next(iter(quote_groups.values()), [])
            resolved = quote[2] if len(quote) > 2 else ''
            if resolved:
                resolved_symbol = f"us{resolved}"
                if resolved_symbol != symbol:
                    resolved_payload, resolved_item = self._request_tencent_history(
                        resolved_symbol, start, end
                    )
                    resolved_rows = (
                        resolved_item.get('day')
                        or resolved_item.get('qfqday')
                        or []
                    )
                    if len(resolved_rows) > len(rows):
                        payload = resolved_payload
                        item = resolved_item
                        rows = resolved_rows

        if not rows:
            message = payload.get('msg') or f"未找到 {market}:{code} 行情"
            raise LookupError(message)

        raw = pd.DataFrame(
            [row[:6] for row in rows if len(row) >= 6],
            columns=[
                'trade_date', 'open', 'close', 'high', 'low', 'volume',
            ],
        )
        return self._normalize_frame(raw, code, market, 'tencent')

    def _request_tencent_history(self, symbol, start, end):
        start_iso = datetime.strptime(start, '%Y%m%d').strftime('%Y-%m-%d')
        end_iso = datetime.strptime(end, '%Y%m%d').strftime('%Y-%m-%d')
        date_count = (
            datetime.strptime(end, '%Y%m%d')
            - datetime.strptime(start, '%Y%m%d')
        ).days
        count = min(max(date_count + 10, 40), 2000)
        timeout = int(self.config.get('global_markets.request_timeout', 30))
        response = self.http.get(
            "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get",
            params={
                'param': (
                    f"{symbol},day,{start_iso},{end_iso},{count},qfq"
                ),
            },
            headers={'User-Agent': 'Mozilla/5.0 stock-analysis-app/2.0'},
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get('code') not in (None, 0):
            raise LookupError(payload.get('msg') or '腾讯行情请求失败')
        item = (payload.get('data') or {}).get(symbol) or {}
        return payload, item

    def _resolve_us_symbol(self, code: str) -> str:
        if code[:3].isdigit() and len(code) > 4 and code[3] == '.':
            return code
        with self._cache_lock:
            if code in self._us_symbol_cache:
                return self._us_symbol_cache[code]

        spot = self.ak.stock_us_spot_em()
        if spot is None or spot.empty or '代码' not in spot.columns:
            raise LookupError(f"无法解析美股代码 {code}")

        for candidate in spot['代码'].astype(str):
            if candidate.upper().split('.')[-1] == code:
                with self._cache_lock:
                    self._us_symbol_cache[code] = candidate
                return candidate
        raise LookupError(f"未找到美股代码 {code}")

    def _normalize_frame(
        self, frame: pd.DataFrame, code: str, market: str, source: str
    ) -> pd.DataFrame:
        if frame is None or frame.empty:
            return pd.DataFrame(columns=self.STANDARD_COLUMNS)

        df = frame.rename(columns={
            'date': 'trade_date',
            '日期': 'trade_date',
            '开盘': 'open',
            '收盘': 'close',
            '最高': 'high',
            '最低': 'low',
            '成交量': 'volume',
            '成交额': 'amount',
            '涨跌幅': 'change_pct',
        }).copy()

        required = {'trade_date', 'open', 'close', 'high', 'low'}
        missing = sorted(required - set(df.columns))
        if missing:
            raise ValueError(f"行情数据缺少字段: {', '.join(missing)}")

        df['trade_date'] = pd.to_datetime(df['trade_date'], errors='coerce')
        df = df.dropna(subset=['trade_date']).sort_values('trade_date')
        for column in ['open', 'close', 'high', 'low', 'volume', 'amount', 'change_pct']:
            if column in df:
                df[column] = pd.to_numeric(df[column], errors='coerce')

        if 'volume' not in df:
            df['volume'] = None
        if 'amount' not in df:
            df['amount'] = None
        if 'change_pct' not in df:
            df['change_pct'] = df['close'].pct_change() * 100

        df['code'] = code
        df['market'] = market
        df['currency'] = MARKETS[market].currency
        df['source'] = source
        df['trade_date'] = df['trade_date'].dt.strftime('%Y-%m-%d')
        return df[self.STANDARD_COLUMNS].reset_index(drop=True)

    @staticmethod
    def _compact_date(value: str) -> str:
        parsed = datetime.strptime(value, '%Y-%m-%d')
        return parsed.strftime('%Y%m%d')

    @staticmethod
    def _default_start_date() -> str:
        return (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')

    @staticmethod
    def _unix_time(value: str) -> int:
        parsed = datetime.strptime(value, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        return int(parsed.timestamp())

    @staticmethod
    def _yahoo_symbol(
        code: str,
        market: str,
        security_type: Optional[str] = None,
    ) -> str:
        if market == 'US':
            if security_type == 'INDEX':
                return '^' + code.lstrip('^')
            return code.split('.', 1)[-1] if code[:3].isdigit() else code
        compact = code.lstrip('0') or '0'
        return f"{compact.zfill(4)}.HK"

    @staticmethod
    def _tencent_symbol(code: str, market: str) -> str:
        if market == 'HK':
            return f"hk{code}"
        index_aliases = {
            'DJI': 'DJI',
            'GSPC': 'INX',
            'IXIC': 'IXIC',
            'RUT': 'RUT',
        }
        return f"us{index_aliases.get(code, code.lstrip('^'))}"


_global_market_data_service = None
_global_market_data_lock = Lock()


def get_global_market_data_service() -> GlobalMarketDataService:
    global _global_market_data_service
    if _global_market_data_service is None:
        with _global_market_data_lock:
            if _global_market_data_service is None:
                _global_market_data_service = GlobalMarketDataService()
    return _global_market_data_service
