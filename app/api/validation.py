"""API 请求参数校验工具。"""

from datetime import datetime


def parse_int(value, name, default=None, minimum=None, maximum=None):
    """解析有界整数，失败时抛出可直接返回给客户端的 ValueError。"""
    if value is None or value == '':
        if default is None:
            raise ValueError(f'{name} 不能为空')
        value = default
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f'{name} 必须是整数') from exc
    if minimum is not None and result < minimum:
        raise ValueError(f'{name} 不能小于 {minimum}')
    if maximum is not None and result > maximum:
        raise ValueError(f'{name} 不能大于 {maximum}')
    return result


def validate_date_range(start_date=None, end_date=None):
    """校验可选的 YYYY-MM-DD 日期范围。"""
    parsed = {}
    for name, value in (('start_date', start_date), ('end_date', end_date)):
        if not value:
            parsed[name] = None
            continue
        try:
            parsed[name] = datetime.strptime(value, '%Y-%m-%d').date()
        except (TypeError, ValueError) as exc:
            raise ValueError(f'{name} 必须是 YYYY-MM-DD 格式') from exc
    if (
        parsed['start_date']
        and parsed['end_date']
        and parsed['start_date'] > parsed['end_date']
    ):
        raise ValueError('start_date 不能晚于 end_date')
