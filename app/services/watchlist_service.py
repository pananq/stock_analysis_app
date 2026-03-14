"""
关注列表服务
"""
import threading
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import pandas as pd
from app.models.orm_models import ORMDatabase, Watchlist, Stock
from app.utils import get_logger, get_config
from sqlalchemy.orm import sessionmaker

logger = get_logger(__name__)


class WatchlistService:
    """关注列表服务类"""

    def __init__(self):
        config = get_config()
        mysql_config = config.get('database.mysql')
        if not mysql_config:
            raise ValueError("未配置MySQL数据库信息")

        mysql_url = (
            f"mysql+pymysql://{mysql_config.get('username')}:"
            f"{mysql_config.get('password')}@"
            f"{mysql_config.get('host')}:"
            f"{mysql_config.get('port')}/"
            f"{mysql_config.get('database')}?charset=utf8mb4"
        )

        self.orm_db = ORMDatabase(mysql_url)
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
            'stock_code': row.stock_code,
            'market': row.market,
            'group_name': row.group_name,
            'tags': self._tags_from_db(row.tags),
            'notes': row.notes,
            'created_at': row.created_at.isoformat() if row.created_at else None,
        }

    def add_stock(self, user_id: int, stock_code: str, market: str = 'CN',
                  group_name: str = None, tags: str = None, notes: str = None) -> dict:
        session = self.Session()
        try:
            # Check if already exists
            existing = session.query(Watchlist).filter(
                Watchlist.user_id == user_id,
                Watchlist.stock_code == stock_code,
                Watchlist.market == market
            ).first()
            if existing:
                return {'success': False, 'error': '已在关注列表中'}

            item = Watchlist(
                user_id=user_id,
                stock_code=stock_code,
                market=market,
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
            return {'success': False, 'error': str(e)}
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
            return False
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
            return {'success': False, 'error': str(e)}
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
            stock_codes = [item.stock_code for item in items]
            stock_map = {}
            if stock_codes:
                stocks = session.query(Stock).filter(Stock.code.in_(stock_codes)).all()
                stock_map = {s.code: s for s in stocks}

            result = []
            for item in items:
                d = self._row_to_dict(item)
                s = stock_map.get(item.stock_code)
                d['stock_name'] = s.name if s else None
                d['industry'] = s.industry if s else None
                d['market_type'] = s.market_type if s else None
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

    def get_stock_data_with_indicators(self, stock_code: str, start_date: str = None,
                                        end_date: str = None, ma_periods: List[int] = None) -> dict:
        if ma_periods is None:
            ma_periods = [5, 30, 60]

        from app.services.market_data_service import get_market_data_service
        from app.indicators.technical_indicators import TechnicalIndicators

        df = get_market_data_service().get_stock_data(stock_code, start_date, end_date)

        if df.empty:
            return {
                'stock_code': stock_code,
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
