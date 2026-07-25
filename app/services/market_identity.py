"""跨市场证券标识和展示信息。"""

import re
from dataclasses import dataclass


SUPPORTED_MARKETS = ('CN', 'HK', 'US')
SUPPORTED_SECURITY_TYPES = ('STOCK', 'ETF', 'FUND', 'INDEX')


@dataclass(frozen=True)
class MarketInfo:
    code: str
    name: str
    currency: str
    timezone: str


MARKETS = {
    'CN': MarketInfo('CN', 'A股', 'CNY', 'Asia/Shanghai'),
    'HK': MarketInfo('HK', '港股', 'HKD', 'Asia/Hong_Kong'),
    'US': MarketInfo('US', '美股', 'USD', 'America/New_York'),
}


def normalize_market(market: str) -> str:
    value = (market or 'CN').strip().upper()
    aliases = {
        'A': 'CN',
        'A股': 'CN',
        'CHINA': 'CN',
        '港股': 'HK',
        'HONGKONG': 'HK',
        'HONG_KONG': 'HK',
        '美股': 'US',
        'USA': 'US',
    }
    value = aliases.get(value, value)
    if value not in SUPPORTED_MARKETS:
        raise ValueError(f"不支持的市场: {market}，可选值为 CN/HK/US")
    return value


def normalize_security_type(security_type: str = 'STOCK') -> str:
    value = (security_type or 'STOCK').strip().upper()
    aliases = {
        '股票': 'STOCK',
        '基金': 'FUND',
        '指数': 'INDEX',
        'ETP': 'ETF',
        'REIT': 'FUND',
    }
    value = aliases.get(value, value)
    if value not in SUPPORTED_SECURITY_TYPES:
        raise ValueError(
            "不支持的证券类型，可选值为 STOCK/ETF/FUND/INDEX"
        )
    return value


def normalize_security_code(
    code: str,
    market: str = 'CN',
    security_type: str = 'STOCK',
) -> str:
    market = normalize_market(market)
    security_type = normalize_security_type(security_type)
    value = (code or '').strip().upper()
    if not value:
        raise ValueError("股票代码不能为空")

    # 允许 API 使用 CN:600000 这种显式标识。
    if ':' in value:
        prefix, raw_code = value.split(':', 1)
        if normalize_market(prefix) != market:
            raise ValueError("股票代码中的市场前缀与 market 参数不一致")
        value = raw_code

    if market == 'CN':
        if security_type == 'INDEX':
            if not re.fullmatch(r'(?:SH|SZ)\d{6}', value):
                raise ValueError("A股指数代码必须使用 SH/SZ 加 6 位数字")
            return value
        value = re.sub(r'^(?:SH|SZ)', '', value)
        value = value.split('.')[0]
        if not re.fullmatch(r'\d{6}', value):
            raise ValueError("A股代码必须是 6 位数字")
    elif market == 'HK':
        if security_type == 'INDEX':
            value = value.lstrip('^')
            if not re.fullmatch(r'[A-Z][A-Z0-9.\-]{0,18}', value):
                raise ValueError("港股指数代码格式无效")
            return value
        value = value.split('.')[0]
        if not value.isdigit() or len(value) > 5:
            raise ValueError("港股代码必须是最多 5 位数字")
        value = value.zfill(5)
    else:
        if security_type == 'INDEX':
            value = value.lstrip('^')
            if not re.fullmatch(r'[.]?[A-Z][A-Z0-9.\-]{0,19}', value):
                raise ValueError("美股指数代码格式无效")
            return value
        # 既接受 AAPL，也接受 AkShare/EastMoney 返回的 105.AAPL。
        if not re.fullmatch(r'(?:\d{3}\.)?[A-Z0-9][A-Z0-9.\-]{0,19}', value):
            raise ValueError("美股代码格式无效")
    return value


def security_key(
    code: str,
    market: str = 'CN',
    security_type: str = 'STOCK',
) -> str:
    market = normalize_market(market)
    security_type = normalize_security_type(security_type)
    return (
        f"{market}:{security_type}:"
        f"{normalize_security_code(code, market, security_type)}"
    )
