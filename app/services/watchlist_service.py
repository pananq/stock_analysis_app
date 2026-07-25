"""
关注列表服务
"""
import threading
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import pandas as pd
from app.models.orm_models import ORMDatabase, Watchlist, Stock
from app.services.market_identity import (
    MARKETS,
    normalize_market,
    normalize_security_code,
    normalize_security_type,
)
from app.utils import get_logger, get_config
from app.utils.database_url import build_mysql_url
from sqlalchemy.orm import sessionmaker

logger = get_logger(__name__)


class WatchlistService:
    """关注列表服务类"""

    def __init__(self, session_factory=None, market_data_resolver=None):
        self.orm_db = None
        self.market_data_resolver = market_data_resolver
        if session_factory is not None:
            self.Session = session_factory
        else:
            config = get_config()
            mysql_config = config.get('database.mysql')
            if not mysql_config:
                raise ValueError("未配置MySQL数据库信息")

            self.orm_db = ORMDatabase(build_mysql_url(mysql_config))
            self.Session = sessionmaker(bind=self.orm_db.engine)
        logger.info("WatchlistService 初始化完成")

    def _tags_to_db(self, tags: Optional[str]) -> Optional[str]:
        """将标签字符串转换为数据库格式 ,tag1,tag2,"""
        if not tags:
            return None
        tags = tags.strip().strip(',')
        if not tags:
            return None
        return ',' + tags + ','

    def _tags_from_db(self, tags_db: Optional[str]) -> Optional[str]:
        """从数据库格式转换为展示格式"""
        if not tags_db:
            return None
        return tags_db.strip(',')

    def _row_to_dict(self, row: Watchlist) -> dict:
        return {
            'id': row.id,
            'user_id': row.user_id,
            'security_id': row.security_id,
            'stock_code': row.stock_code,
            'market': row.market,
            'security_type': row.security_type or 'STOCK',
            'group_name': row.group_name,
            'tags': self._tags_from_db(row.tags),
            'notes': row.notes,
            'created_at': row.created_at.isoformat() if row.created_at else None,
        }

    def add_stock(self, user_id: int, stock_code: str, market: str = 'CN',
                  security_type: str = 'STOCK', group_name: str = None,
                  tags: str = None, notes: str = None) -> dict:
        market = normalize_market(market)
        security_type = normalize_security_type(security_type)
        stock_code = normalize_security_code(
            stock_code, market, security_type
        )
        session = self.Session()
        try:
            stock = session.query(Stock).filter(
                Stock.market == market,
                Stock.code == stock_code,
                Stock.security_type == security_type,
            ).first()
            if not stock:
                return {'success': False, 'error': '证券目录中不存在该证券'}

            # Check if already exists
            existing = session.query(Watchlist).filter(
                Watchlist.user_id == user_id,
                Watchlist.security_id == stock.id,
            ).first()
            if existing:
                return {'success': False, 'error': '已在关注列表中'}

            item = Watchlist(
                user_id=user_id,
                security_id=stock.id,
                stock_code=stock_code,
                market=market,
                security_type=security_type,
                group_name=group_name,
                tags=self._tags_to_db(tags),
                notes=notes,
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            return {'success': True, 'data': self._row_to_dict(item)}
        except Exception as e:
            session.rollback()
            logger.error(f"添加关注股票失败: {e}")
            raise
        finally:
            session.close()

    def remove_stock(self, user_id: int, watchlist_id: int) -> bool:
        session = self.Session()
        try:
            count = session.query(Watchlist).filter(
                Watchlist.id == watchlist_id,
                Watchlist.user_id == user_id
            ).delete()
            session.commit()
            return count > 0
        except Exception as e:
            session.rollback()
            logger.error(f"删除关注股票失败: {e}")
            raise
        finally:
            session.close()

    def update_stock(self, user_id: int, watchlist_id: int, **kwargs) -> dict:
        session = self.Session()
        try:
            item = session.query(Watchlist).filter(
                Watchlist.id == watchlist_id,
                Watchlist.user_id == user_id
            ).first()
            if not item:
                return {'success': False, 'error': '记录不存在'}

            if 'group_name' in kwargs:
                item.group_name = kwargs['group_name']
            if 'tags' in kwargs:
                item.tags = self._tags_to_db(kwargs['tags'])
            if 'notes' in kwargs:
                item.notes = kwargs['notes']

            session.commit()
            session.refresh(item)
            return {'success': True, 'data': self._row_to_dict(item)}
        except Exception as e:
            session.rollback()
            logger.error(f"更新关注股票失败: {e}")
            raise
        finally:
            session.close()

    def get_watchlist(self, user_id: int, group_name: str = None, tag: str = None) -> List[dict]:
        session = self.Session()
        try:
            query = session.query(Watchlist).filter(Watchlist.user_id == user_id)
            if group_name:
                query = query.filter(Watchlist.group_name == group_name)
            if tag:
                query = query.filter(Watchlist.tags.like(f'%,{tag},%'))
            items = query.order_by(Watchlist.created_at.desc()).all()

            # Batch-fetch stock metadata to avoid N+1 queries
            stock_map = {}
            security_ids = {item.security_id for item in items}
            if security_ids:
                stocks = session.query(Stock).filter(
                    Stock.id.in_(security_ids)
                ).all()
                stock_map = {stock.id: stock for stock in stocks}

            result = []
            for item in items:
                d = self._row_to_dict(item)
                s = stock_map.get(item.security_id)
                d['stock_name'] = s.name if s else None
                d['industry'] = s.industry if s else None
                d['market_type'] = s.market_type if s else MARKETS[item.market].name
                d['currency'] = MARKETS[item.market].currency
                result.append(d)
            return result
        finally:
            session.close()

    def get_item(self, user_id: int, watchlist_id: int) -> Optional[dict]:
        session = self.Session()
        try:
            item = session.query(Watchlist).filter(
                Watchlist.id == watchlist_id,
                Watchlist.user_id == user_id
            ).first()
            return self._row_to_dict(item) if item else None
        finally:
            session.close()

    def get_stock_dataframe(
        self,
        stock_code: str,
        market: str = 'CN',
        security_type: str = 'STOCK',
        start_date: str = None,
        end_date: str = None,
    ) -> pd.DataFrame:
        market = normalize_market(market)
        security_type = normalize_security_type(security_type)
        stock_code = normalize_security_code(
            stock_code, market, security_type
        )
        if self.market_data_resolver is not None:
            return self.market_data_resolver(
                stock_code,
                market,
                security_type,
                start_date,
                end_date,
            )
        from app.services.security_market_data_service import (
            get_security_market_data_service,
        )
        return get_security_market_data_service().get_daily_data(
            stock_code,
            market=market,
            security_type=security_type,
            start_date=start_date,
            end_date=end_date,
        )

    def get_stock_data_with_indicators(
        self,
        stock_code: str,
        market: str = 'CN',
        security_type: str = 'STOCK',
        start_date: str = None,
        end_date: str = None,
        ma_periods: List[int] = None,
    ) -> dict:
        if ma_periods is None:
            ma_periods = [5, 30, 60]
        ma_periods = sorted(set(ma_periods))
        if (
            not ma_periods
            or len(ma_periods) > 10
            or any(period < 1 or period > 250 for period in ma_periods)
        ):
            raise ValueError("均线周期必须为 1-250 之间的整数，且最多 10 个")

        from app.indicators.technical_indicators import TechnicalIndicators

        market = normalize_market(market)
        security_type = normalize_security_type(security_type)
        stock_code = normalize_security_code(
            stock_code, market, security_type
        )
        df = self.get_stock_dataframe(
            stock_code,
            market,
            security_type,
            start_date,
            end_date,
        )

        if df.empty:
            return {
                'stock_code': stock_code,
                'market': market,
                'security_type': security_type,
                'currency': MARKETS[market].currency,
                'records': [],
                'summary': {'avg_price': None, 'max_price': None, 'record_count': 0},
                'indicators': {}
            }

        df = TechnicalIndicators.calculate_ma(df, periods=ma_periods)

        avg_price = float(df['close'].mean()) if not df['close'].isna().all() else None
        max_price = float(df['high'].max()) if not df['high'].isna().all() else None

        # Build records
        records = []
        for _, row in df.iterrows():
            record = {
                'trade_date': str(row['trade_date']),
                'open': round(float(row['open']), 4) if pd.notna(row.get('open')) else None,
                'close': round(float(row['close']), 4) if pd.notna(row.get('close')) else None,
                'high': round(float(row['high']), 4) if pd.notna(row.get('high')) else None,
                'low': round(float(row['low']), 4) if pd.notna(row.get('low')) else None,
                'volume': int(row['volume']) if pd.notna(row.get('volume')) else None,
                'change_pct': round(float(row['change_pct']), 4) if pd.notna(row.get('change_pct')) else None,
            }
            records.append(record)

        # Build indicators
        indicators = {}
        for period in ma_periods:
            col = f'ma_{period}'
            if col in df.columns:
                indicators[col] = [
                    {'trade_date': str(df.iloc[i]['trade_date']), 'value': round(float(df.iloc[i][col]), 4) if pd.notna(df.iloc[i][col]) else None}
                    for i in range(len(df))
                ]

        return {
            'stock_code': stock_code,
            'market': market,
            'security_type': security_type,
            'currency': MARKETS[market].currency,
            'records': records,
            'summary': {
                'avg_price': round(avg_price, 4) if avg_price else None,
                'max_price': round(max_price, 4) if max_price else None,
                'record_count': len(records),
            },
            'indicators': indicators
        }


# Singleton
_watchlist_service_instance = None
_watchlist_service_lock = threading.Lock()


def get_watchlist_service() -> WatchlistService:
    global _watchlist_service_instance
    if _watchlist_service_instance is None:
        with _watchlist_service_lock:
            if _watchlist_service_instance is None:
                _watchlist_service_instance = WatchlistService()
    return _watchlist_service_instance
