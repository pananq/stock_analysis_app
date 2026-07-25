"""数据库连接 URL 的安全构造工具。"""

from typing import Any, Mapping

from sqlalchemy.engine import URL


def build_mysql_url(
    config: Mapping[str, Any],
    *,
    include_database: bool = True,
) -> URL:
    """构造能够正确转义用户名和密码特殊字符的 SQLAlchemy URL。"""
    database = config.get('database') if include_database else None
    return URL.create(
        drivername='mysql+pymysql',
        username=config.get('username', 'root'),
        password=config.get('password', ''),
        host=config.get('host', 'localhost'),
        port=int(config.get('port', 3306)),
        database=database,
        query={'charset': str(config.get('charset', 'utf8mb4'))},
    )
