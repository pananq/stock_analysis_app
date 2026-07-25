"""跨市场证券代码列表获取与标准化。"""

from io import BytesIO, StringIO
from typing import Dict, Optional, Tuple

import pandas as pd
import requests

from app.services.market_identity import normalize_security_code
from app.utils import get_config, get_logger


logger = get_logger(__name__)


class SecurityListService:
    """从交易所官方目录获取港股和美股证券列表。"""

    HKEX_SECURITIES_URL = (
        "https://www.hkex.com.hk/eng/services/trading/securities/"
        "securitieslists/ListOfSecurities.xlsx"
    )
    NASDAQ_LISTED_URL = (
        "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
    )
    NASDAQ_OTHER_LISTED_URL = (
        "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"
    )

    COLUMNS = (
        'code',
        'name',
        'list_date',
        'industry',
        'market_type',
        'security_type',
        'status',
    )

    US_MAJOR_INDICES = (
        ('GSPC', 'S&P 500'),
        ('IXIC', 'NASDAQ Composite'),
        ('DJI', 'Dow Jones Industrial Average'),
        ('RUT', 'Russell 2000'),
    )

    def __init__(
        self,
        config=None,
        http_get=None,
        akshare_client=None,
    ):
        self.config = config or get_config()
        self.http_get = http_get or requests.get
        self.akshare = akshare_client

    def get_global_stock_lists(
        self,
    ) -> Tuple[Dict[str, pd.DataFrame], Dict[str, str]]:
        """
        获取港股和美股列表。

        单个市场失败不会阻止另一个市场返回；调用方可据此保留失败
        市场在数据库中的旧数据。
        """
        frames: Dict[str, pd.DataFrame] = {}
        errors: Dict[str, str] = {}

        for market, loader in (
            ('HK', self.get_hk_stock_list),
            ('US', self.get_us_stock_list),
        ):
            try:
                frame = loader()
                if frame.empty:
                    raise ValueError(f"{market} 股票列表为空")
                frames[market] = frame
            except Exception as exc:
                errors[market] = str(exc)
                logger.warning("获取 %s 股票列表失败: %s", market, exc)

        return frames, errors

    def get_catalog_parts(
        self,
    ) -> Tuple[Dict[str, pd.DataFrame], Dict[str, str]]:
        """按市场和证券类型独立抓取目录，便于失败时保留旧数据。"""
        parts: Dict[str, pd.DataFrame] = {}
        errors: Dict[str, str] = {}
        loaders = (
            ('CN_ETF', self.get_cn_etf_list),
            ('CN_FUND', self.get_cn_fund_list),
            ('CN_INDEX', self.get_cn_index_list),
            ('HK_LIST', self.get_hk_stock_list),
            ('HK_INDEX', self.get_hk_index_list),
            ('US_LIST', self.get_us_stock_list),
            ('US_INDEX', self.get_us_index_list),
        )
        for scope, loader in loaders:
            try:
                frame = loader()
                if frame.empty:
                    raise ValueError(f"{scope} 证券列表为空")
                if scope.endswith('_LIST'):
                    market = scope.split('_', 1)[0]
                    for security_type, group in frame.groupby('security_type'):
                        parts[f'{market}_{security_type}'] = (
                            group.reset_index(drop=True)
                        )
                else:
                    parts[scope] = frame
            except Exception as exc:
                errors[scope] = str(exc)
                logger.warning("获取 %s 证券列表失败: %s", scope, exc)
        return parts, errors

    def get_hk_stock_list(self) -> pd.DataFrame:
        """优先使用 HKEX 完整清单，失败后降级到 AkShare。"""
        try:
            response = self._request(self.HKEX_SECURITIES_URL)
            raw = pd.read_excel(
                BytesIO(response.content),
                sheet_name='ListOfSecurities',
                header=2,
                dtype={'Stock Code': str},
            )
            category = raw['Category'].astype(str).str.strip()
            supported = {
                'Equity': 'STOCK',
                'Exchange Traded Products': 'ETF',
                'Real Estate Investment Trusts': 'FUND',
            }
            raw = raw.loc[category.isin(supported)].copy()
            raw['security_type'] = category.loc[raw.index].map(supported)
            frame = pd.DataFrame({
                'code': raw['Stock Code'],
                'name': raw['Name of Securities'],
                'security_type': raw['security_type'],
            })
            result = self._standardize(frame, 'HK')
            if result.empty:
                raise ValueError("HKEX 返回的股票列表为空")
            logger.info("从 HKEX 获取 %s 只港股", len(result))
            return result
        except Exception as official_error:
            logger.warning("HKEX 股票列表不可用，尝试 AkShare: %s", official_error)
            return self._get_hk_list_from_akshare()

    def get_us_stock_list(self) -> pd.DataFrame:
        """合并 Nasdaq 与其他美国交易所的官方证券目录。"""
        try:
            nasdaq = self._read_pipe_directory(
                self.NASDAQ_LISTED_URL,
                symbol_column='Symbol',
            )
            other = self._read_pipe_directory(
                self.NASDAQ_OTHER_LISTED_URL,
                symbol_column='ACT Symbol',
            )
            result = self._standardize(
                pd.concat([nasdaq, other], ignore_index=True),
                'US',
            )
            if result.empty:
                raise ValueError("Nasdaq Trader 返回的股票列表为空")
            logger.info("从 Nasdaq Trader 获取 %s 只美股", len(result))
            return result
        except Exception as official_error:
            logger.warning(
                "Nasdaq Trader 股票列表不可用，尝试 AkShare: %s",
                official_error,
            )
            return self._get_us_list_from_akshare()

    def _read_pipe_directory(
        self,
        url: str,
        symbol_column: str,
    ) -> pd.DataFrame:
        response = self._request(url)
        raw = pd.read_csv(
            StringIO(response.text),
            sep='|',
            dtype=str,
            keep_default_na=False,
        )
        raw = raw.loc[raw.get('Test Issue', '').astype(str).eq('N')]
        return pd.DataFrame({
            'code': raw[symbol_column],
            'name': raw['Security Name'],
            'security_type': raw['ETF'].map(
                lambda value: 'ETF' if str(value) == 'Y' else 'STOCK'
            ),
        })

    def get_cn_etf_list(self) -> pd.DataFrame:
        raw = self._get_akshare().fund_etf_category_sina('ETF基金')
        return self._standardize(
            pd.DataFrame({'code': raw['代码'], 'name': raw['名称']}),
            'CN',
            'ETF',
        )

    def get_cn_fund_list(self) -> pd.DataFrame:
        ak = self._get_akshare()
        frames = []
        errors = []
        for category in ('LOF基金', '封闭式基金'):
            try:
                raw = ak.fund_etf_category_sina(category)
                frames.append(pd.DataFrame({
                    'code': raw['代码'],
                    'name': raw['名称'],
                }))
            except Exception as exc:
                errors.append(f"{category}: {exc}")
        if not frames:
            raise RuntimeError('；'.join(errors) or 'CN 基金列表不可用')
        return self._standardize(
            pd.concat(frames, ignore_index=True),
            'CN',
            'FUND',
        )

    def get_cn_index_list(self) -> pd.DataFrame:
        raw = self._get_akshare().stock_zh_index_spot_sina()
        return self._standardize(
            pd.DataFrame({'code': raw['代码'], 'name': raw['名称']}),
            'CN',
            'INDEX',
        )

    def get_hk_index_list(self) -> pd.DataFrame:
        raw = self._get_akshare().stock_hk_index_spot_sina()
        return self._standardize(
            pd.DataFrame({'code': raw['代码'], 'name': raw['名称']}),
            'HK',
            'INDEX',
        )

    def get_us_index_list(self) -> pd.DataFrame:
        return self._standardize(
            pd.DataFrame(
                self.US_MAJOR_INDICES,
                columns=['code', 'name'],
            ),
            'US',
            'INDEX',
        )

    def _get_hk_list_from_akshare(self) -> pd.DataFrame:
        ak = self._get_akshare()
        errors = []
        for method_name, code_column, name_column in (
            ('stock_hk_spot_em', '代码', '名称'),
            ('stock_hk_spot', 'symbol', 'name'),
        ):
            try:
                raw = getattr(ak, method_name)()
                result = self._standardize(
                    pd.DataFrame({
                        'code': raw[code_column],
                        'name': raw[name_column],
                    }),
                    'HK',
                )
                if not result.empty:
                    logger.info(
                        "从 AkShare %s 获取 %s 只港股",
                        method_name,
                        len(result),
                    )
                    return result
            except Exception as exc:
                errors.append(f"{method_name}: {exc}")
        raise RuntimeError("；".join(errors) or "AkShare 港股列表不可用")

    def _get_us_list_from_akshare(self) -> pd.DataFrame:
        ak = self._get_akshare()
        try:
            raw = ak.stock_us_spot_em()
            codes = raw['代码'].astype(str).str.replace(
                r'^\d{3}\.',
                '',
                regex=True,
            )
            result = self._standardize(
                pd.DataFrame({'code': codes, 'name': raw['名称']}),
                'US',
            )
            if result.empty:
                raise ValueError("AkShare 美股列表为空")
            logger.info("从 AkShare 获取 %s 只美股", len(result))
            return result
        except Exception as exc:
            raise RuntimeError(f"stock_us_spot_em: {exc}") from exc

    def _standardize(
        self,
        frame: pd.DataFrame,
        market: str,
        security_type: Optional[str] = None,
    ) -> pd.DataFrame:
        rows = []
        for _, item in frame.iterrows():
            raw_code = item['code']
            raw_name = item['name']
            item_type = str(
                item.get('security_type') or security_type or 'STOCK'
            ).upper()
            try:
                code = normalize_security_code(
                    str(raw_code),
                    market,
                    item_type,
                )
            except ValueError:
                continue
            name = str(raw_name or '').strip()
            if not name or name.lower() == 'nan':
                continue
            rows.append({
                'code': code,
                'name': name,
                'list_date': None,
                'industry': None,
                'market_type': market,
                'security_type': item_type,
                'status': 'normal',
            })

        if not rows:
            return pd.DataFrame(columns=self.COLUMNS)
        return (
            pd.DataFrame(rows, columns=self.COLUMNS)
            .drop_duplicates(subset=['code'], keep='first')
            .sort_values('code')
            .reset_index(drop=True)
        )

    def _request(self, url: str):
        timeout = int(
            self.config.get('global_markets.request_timeout', 30)
        )
        response = self.http_get(
            url,
            timeout=timeout,
            headers={'User-Agent': 'stock-analysis-app/2.0'},
        )
        response.raise_for_status()
        return response

    def _get_akshare(self):
        if self.akshare is None:
            import akshare as ak

            self.akshare = ak
        return self.akshare
