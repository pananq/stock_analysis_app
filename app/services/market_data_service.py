"""
历史行情数据管理服务
负责股票历史行情数据的获取、存储和查询
"""
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime, timedelta, date
import math
import numbers
import pandas as pd
from app.models.orm_models import DailyMarket, ORMDatabase, Stock
from app.models.mysql_db import get_mysql_db
from app.services import get_datasource, get_stock_service
from app.services.market_identity import (
    SUPPORTED_MARKETS,
    normalize_market,
)
from app.services.stock_date_range_service import StockDateRangeService
from app.utils import get_logger, get_rate_limiter, get_config, get_stock_limit_for_mode
from app.utils.database_url import build_mysql_url
from sqlalchemy import func
from sqlalchemy.orm import sessionmaker

logger = get_logger(__name__)


class MarketDataService:
    """历史行情数据管理服务类"""
    
    def __init__(self):
        """初始化行情数据服务"""
        self.logger = get_logger(__name__)
        self.datasource = get_datasource()
        self.stock_service = get_stock_service()
        self.rate_limiter = get_rate_limiter()
        self.config = get_config()
        
        # 创建ORM数据库连接
        mysql_config = self.config.get('database.mysql')
        if not mysql_config:
            raise ValueError("未配置MySQL数据库信息")
        
        self.orm_db = ORMDatabase(build_mysql_url(mysql_config))
        self.Session = sessionmaker(bind=self.orm_db.engine)
        
        # 创建日期范围服务
        self.date_range_service = StockDateRangeService(get_mysql_db())
        self._security_market_router = None
        
        self.logger.info("行情数据服务初始化完成")

    @staticmethod
    def _normalize_markets(markets=None) -> List[str]:
        """标准化批量任务市场；未指定时始终覆盖全部支持市场。"""
        if markets is None:
            values = list(SUPPORTED_MARKETS)
        elif isinstance(markets, str):
            values = [
                item.strip()
                for item in markets.split(',')
                if item.strip()
            ]
        else:
            values = list(markets)

        normalized = []
        for value in values:
            market = normalize_market(value)
            if market not in normalized:
                normalized.append(market)
        if not normalized:
            raise ValueError("批量行情任务至少需要一个市场")
        return normalized

    def _load_market_securities(
        self,
        markets=None,
        only_existing: bool = False,
    ):
        """
        分市场读取证券并轮询排列，防止长任务始终先处理 A 股。

        返回顺序固定为 CN、HK、US 逐轮交替；若请求市场在目录中没有
        可处理证券则直接失败，避免任务仅更新单一市场却报告成功。
        """
        requested_markets = self._normalize_markets(markets)
        existing_codes = None
        if only_existing:
            session = self.Session()
            try:
                rows = session.query(DailyMarket.security_id).distinct().all()
                existing_codes = {row[0] for row in rows}
            finally:
                session.close()

        groups = {}
        missing_markets = []
        for market in requested_markets:
            securities = self.stock_service.get_stock_list(
                market_type=market,
            )
            decorated = []
            for security in securities:
                item = dict(security)
                item['market'] = market
                item['security_type'] = str(
                    item.get('security_type') or 'STOCK'
                ).upper()
                if existing_codes is None or item['id'] in existing_codes:
                    decorated.append(item)
            groups[market] = decorated
            if not decorated:
                missing_markets.append(market)

        if missing_markets:
            mode = "已有行情" if only_existing else "证券目录"
            raise ValueError(
                f"{mode}中缺少市场：{', '.join(missing_markets)}；"
                "已中止任务，避免只更新单一市场"
            )

        ordered = []
        max_size = max(len(items) for items in groups.values())
        for index in range(max_size):
            for market in requested_markets:
                if index < len(groups[market]):
                    ordered.append(groups[market][index])
        return ordered, requested_markets

    @staticmethod
    def _build_market_stats(securities, markets):
        stats = {
            market: {
                'total': 0,
                'attempted': 0,
                'success': 0,
                'failed': 0,
                'skipped': 0,
                'records': 0,
            }
            for market in markets
        }
        for security in securities:
            stats[security['market']]['total'] += 1
        return stats

    @staticmethod
    def _assert_selected_market_coverage(securities, markets):
        selected = {security['market'] for security in securities}
        missing = [market for market in markets if market not in selected]
        if missing:
            raise ValueError(
                "任务的 skip/limit 参数排除了市场："
                f"{', '.join(missing)}；请扩大处理数量"
            )

    @staticmethod
    def _market_errors(market_stats):
        errors = {}
        for market, stats in market_stats.items():
            if stats['total'] <= 0:
                errors[market] = '没有待处理证券'
            elif stats['attempted'] <= 0 and stats['skipped'] <= 0:
                errors[market] = '没有执行任何行情请求'
            elif stats['success'] <= 0 and stats['skipped'] <= 0:
                errors[market] = '没有成功写入行情数据'
        return errors
    
    def import_all_history(self, start_date: str = None, end_date: str = None,
                          limit: int = None, skip: int = 0, 
                          markets=None,
                          progress_callback: Callable = None,
                          stop_event = None) -> Dict[str, Any]:
        """
        全量导入所有股票的历史行情数据
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)，默认为3年前
            end_date: 结束日期 (YYYY-MM-DD)，默认为今天
            limit: 限制导入的股票数量（用于测试），如果为None则根据配置自动确定
            skip: 跳过前N只股票
            markets: 市场列表，默认 CN/HK/US
            progress_callback: 进度回调函数 callback(progress: float, message: str)
            stop_event: 停止事件，用于取消任务
            
        Returns:
            包含执行结果的字典
        """
        self.logger.info("=" * 60)
        self.logger.info("开始全量导入历史行情数据")
        self.logger.info("=" * 60)
        
        start_time = datetime.now()
        
        # 检查是否已取消
        if stop_event and stop_event.is_set():
            return {
                'success': False,
                'message': '任务已取消',
                'cancelled': True
            }
        
        # 设置默认日期范围
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if not start_date:
            # 默认导入3年历史数据
            start_date = (datetime.now() - timedelta(days=365*3)).strftime('%Y-%m-%d')
        
        self.logger.info(f"日期范围: {start_date} 至 {end_date}")
        
        if progress_callback:
            progress_callback(0, f"准备导入数据，日期范围：{start_date} 至 {end_date}")
        
        # 分市场读取并交错排序，确保长任务持续覆盖 CN/HK/US。
        stocks, requested_markets = self._load_market_securities(
            markets=markets,
        )
        total_stocks = len(stocks)
        
        # 应用skip和limit
        if skip > 0:
            stocks = stocks[skip:]
            self.logger.info(f"跳过前{skip}只股票")
        
        # 如果没有显式指定limit，则根据配置自动应用限制
        if limit is None:
            limit = get_stock_limit_for_mode()
            if limit:
                self.logger.info(f"开发模式：限制导入{limit}只股票")
        
        if limit:
            stocks = stocks[:limit]
            self.logger.info(f"限制导入{limit}只股票（测试模式）")

        self._assert_selected_market_coverage(
            stocks,
            requested_markets,
        )
        market_stats = self._build_market_stats(
            stocks,
            requested_markets,
        )
        
        self.logger.info(f"待导入股票数量: {len(stocks)}/{total_stocks}")
        self.logger.info(
            "覆盖市场: %s",
            ', '.join(requested_markets),
        )
        
        if progress_callback:
            progress_callback(
                1,
                f"待导入 {len(stocks)} 只证券，覆盖 "
                f"{'/'.join(requested_markets)}",
            )
        
        # 统计信息
        success_count = 0
        fail_count = 0
        total_records = 0
        failed_stocks = []
        
        # 逐个股票导入
        for idx, stock in enumerate(stocks, 1):
            # 检查是否已取消
            if stop_event and stop_event.is_set():
                self.logger.warning(f"任务被取消，停止导入。已完成 {idx-1}/{len(stocks)} 只股票")
                if progress_callback:
                    progress_callback(
                        ((idx-1) / len(stocks)) * 100,
                        f"任务已取消。已完成 {idx-1}/{len(stocks)} 只股票"
                    )
                return {
                    'success': False,
                    'message': '任务已取消',
                    'cancelled': True,
                    'success_count': success_count,
                    'fail_count': fail_count,
                    'total_records': total_records,
                    'failed_stocks': failed_stocks,
                    'date_range': f"{start_date} 至 {end_date}",
                    'markets': requested_markets,
                    'market_stats': market_stats,
                }
            
            code = stock['code']
            security_id = stock['id']
            name = stock['name']
            market = stock['market']
            security_type = stock['security_type']
            market_stats[market]['attempted'] += 1
            
            try:
                self.logger.info(
                    f"[{idx}/{len(stocks)}][{market}/{security_type}] "
                    f"正在导入 {code} - {name}"
                )
                
                # API频率控制
                self.rate_limiter.wait()
                
                # 获取历史行情数据
                df = self._fetch_security_daily_data(
                    stock, start_date, end_date
                )
                
                if df.empty:
                    self.logger.warning(f"  {code} 未获取到数据")
                    fail_count += 1
                    market_stats[market]['failed'] += 1
                    failed_stocks.append({
                        'code': code,
                        'name': name,
                        'market': market,
                        'security_type': security_type,
                        'reason': '未获取到数据',
                    })
                    
                    # 记录失败的详细信息
                    if progress_callback:
                        progress_callback(
                            (idx / len(stocks)) * 100,
                            f"导入 {code} 失败",
                            stock_code=code,
                            stock_name=name,
                            market=market,
                            security_type=security_type,
                            success=False,
                            records=0,
                            start_date=start_date,
                            end_date=end_date,
                            error='未获取到数据'
                        )
                    continue
                
                # 保存到DuckDB
                records = len(df)
                self._save_daily_data(
                    df,
                    code,
                    security_id=security_id,
                )
                
                # 全量导入后，从 daily_market 表重新计算完整的日期范围并更新 stocks 表
                try:
                    earliest, latest = (
                        self.date_range_service
                        .get_stock_date_range_from_daily_market(
                            code,
                            security_id=security_id,
                        )
                    )
                    if earliest and latest:
                        success = self.date_range_service.update_stock_date_range(
                            code,
                            earliest_date=earliest,
                            latest_date=latest,
                            security_id=security_id,
                        )
                        if success:
                            self.logger.debug(f"  {code} 更新日期范围: {earliest} ~ {latest}")
                except Exception as e:
                    # 日期字段更新失败不应影响主流程
                    self.logger.error(f"  {code} 更新日期范围时发生错误: {e}", exc_info=True)
                
                success_count += 1
                total_records += records
                market_stats[market]['success'] += 1
                market_stats[market]['records'] += records
                self.logger.info(f"  ✓ {code} 导入成功，{records}条记录")
                
                # 记录成功的详细信息
                if progress_callback:
                    progress_callback(
                        (idx / len(stocks)) * 100,
                        f"导入 {code} 成功",
                        stock_code=code,
                        stock_name=name,
                        market=market,
                        security_type=security_type,
                        success=True,
                        records=records,
                        start_date=start_date,
                        end_date=end_date
                    )
                
                # 每10只股票显示一次进度
                if idx % 10 == 0:
                    elapsed = (datetime.now() - start_time).total_seconds()
                    avg_time = elapsed / idx
                    remaining = avg_time * (len(stocks) - idx)
                    progress = (idx / len(stocks)) * 100
                    
                    self.logger.info(f"进度: {idx}/{len(stocks)} ({progress:.1f}%), "
                              f"预计剩余时间: {remaining/60:.1f}分钟")
                    
                    if progress_callback:
                        progress_callback(
                            progress, 
                            f"正在导入... {idx}/{len(stocks)} ({progress:.1f}%), "
                            f"预计剩余 {remaining/60:.1f} 分钟"
                        )
                
            except Exception as e:
                self.logger.error(f"  ✗ {code} 导入失败: {e}")
                fail_count += 1
                market_stats[market]['failed'] += 1
                failed_stocks.append({
                    'code': code,
                    'name': name,
                    'market': market,
                    'security_type': security_type,
                    'reason': str(e),
                })
                
                # 记录失败的详细信息
                if progress_callback:
                    progress_callback(
                        (idx / len(stocks)) * 100,
                        f"导入 {code} 失败",
                        stock_code=code,
                        stock_name=name,
                        market=market,
                        security_type=security_type,
                        success=False,
                        records=0,
                        start_date=start_date,
                        end_date=end_date,
                        error=str(e)
                    )
        
        # 完成统计
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        self.logger.info("=" * 60)
        self.logger.info("全量导入完成")
        self.logger.info(f"总股票数: {len(stocks)}")
        self.logger.info(f"成功: {success_count}")
        self.logger.info(f"失败: {fail_count}")
        self.logger.info(f"总记录数: {total_records}")
        self.logger.info(f"分市场统计: {market_stats}")
        self.logger.info(f"耗时: {duration/60:.2f}分钟")
        self.logger.info("=" * 60)
        
        if failed_stocks:
            self.logger.warning(f"失败的股票列表（前10个）:")
            for stock in failed_stocks[:10]:
                self.logger.warning(f"  {stock['code']} - {stock['name']}: {stock['reason']}")
        
        if progress_callback:
            progress_callback(100, f"导入完成！成功 {success_count} 只，失败 {fail_count} 只，共 {total_records} 条记录")

        market_errors = self._market_errors(market_stats)
        
        return {
            'success': not market_errors,
            'total_stocks': len(stocks),
            'success_count': success_count,
            'fail_count': fail_count,
            'total_records': total_records,
            'duration': duration,
            'failed_stocks': failed_stocks,
            'date_range': f"{start_date} 至 {end_date}",
            'markets': requested_markets,
            'market_stats': market_stats,
            'market_errors': market_errors,
        }
    
    def update_recent_data(self, days: int = 5, only_existing: bool = False,
                          markets=None,
                          progress_callback: Callable = None,
                          stop_event = None) -> Dict[str, Any]:
        """
        增量更新最近N天的行情数据
        
        Args:
            days: 更新最近N天的数据
            only_existing: 是否只更新已有数据的证券（默认False）
            markets: 市场列表，默认 CN/HK/US
            progress_callback: 进度回调函数 callback(progress: float, message: str)
            stop_event: 停止事件，用于取消任务
            
        Returns:
            包含执行结果的字典
        """
        self.logger.info("=" * 60)
        self.logger.info(f"开始增量更新最近{days}天的行情数据")
        self.logger.info("=" * 60)
        
        start_time = datetime.now()
        
        # 检查是否已取消
        if stop_event and stop_event.is_set():
            return {
                'success': False,
                'message': '任务已取消',
                'cancelled': True
            }
        
        # 计算日期范围
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        self.logger.info(f"日期范围: {start_date} 至 {end_date}")
        
        if progress_callback:
            progress_callback(0, f"准备更新数据，日期范围：{start_date} 至 {end_date}")
        
        stocks, requested_markets = self._load_market_securities(
            markets=markets,
            only_existing=only_existing,
        )
        market_stats = self._build_market_stats(
            stocks,
            requested_markets,
        )
        self.logger.info(
            "更新%s，覆盖市场: %s",
            '已有行情证券' if only_existing else '目录中全部证券',
            ', '.join(requested_markets),
        )
        
        self.logger.info(f"待更新股票数量: {len(stocks)}")
        
        if progress_callback:
            progress_callback(
                1,
                f"待更新 {len(stocks)} 只证券，覆盖 "
                f"{'/'.join(requested_markets)}",
            )
        
        # 统计信息
        success_count = 0
        fail_count = 0
        total_records = 0
        failed_stocks = []
        
        # 逐个股票更新
        for idx, stock in enumerate(stocks, 1):
            # 检查是否已取消
            if stop_event and stop_event.is_set():
                self.logger.warning(f"任务被取消，停止更新。已完成 {idx-1}/{len(stocks)} 只股票")
                if progress_callback:
                    progress_callback(
                        ((idx-1) / len(stocks)) * 100,
                        f"任务已取消。已完成 {idx-1}/{len(stocks)} 只股票"
                    )
                return {
                    'success': False,
                    'message': '任务已取消',
                    'cancelled': True,
                    'success_count': success_count,
                    'fail_count': fail_count,
                    'total_records': total_records,
                    'failed_stocks': failed_stocks,
                    'date_range': f"{start_date} 至 {end_date}",
                    'markets': requested_markets,
                    'market_stats': market_stats,
                }
            
            code = stock['code']
            security_id = stock['id']
            name = stock['name']
            market = stock['market']
            security_type = stock['security_type']
            market_stats[market]['attempted'] += 1
            
            try:
                # API频率控制
                self.rate_limiter.wait()
                
                # 获取最近的行情数据
                df = self._fetch_security_daily_data(
                    stock, start_date, end_date
                )
                
                if df.empty:
                    fail_count += 1
                    market_stats[market]['failed'] += 1
                    failed_stocks.append({
                        'code': code,
                        'name': name,
                        'market': market,
                        'security_type': security_type,
                        'reason': '未获取到数据',
                    })
                    if progress_callback:
                        progress_callback(
                            (idx / len(stocks)) * 100,
                            f"[{market}] 更新 {code} 失败",
                            stock_code=code,
                            stock_name=name,
                            market=market,
                            security_type=security_type,
                            success=False,
                            records=0,
                            start_date=start_date,
                            end_date=end_date,
                            error='未获取到数据',
                        )
                    continue
                
                # 删除该股票在日期范围内的旧数据
                self._delete_data_in_range(
                    security_id,
                    start_date,
                    end_date,
                )
                
                # 保存新数据
                records = len(df)
                self._save_daily_data(
                    df,
                    code,
                    security_id=security_id,
                )
                
                success_count += 1
                total_records += records
                market_stats[market]['success'] += 1
                market_stats[market]['records'] += records
                if progress_callback:
                    progress_callback(
                        (idx / len(stocks)) * 100,
                        f"[{market}] 更新 {code} 成功",
                        stock_code=code,
                        stock_name=name,
                        market=market,
                        security_type=security_type,
                        success=True,
                        records=records,
                        start_date=start_date,
                        end_date=end_date,
                    )
                
                # 每10只股票显示一次进度
                if idx % 10 == 0:
                    progress = (idx / len(stocks)) * 100
                    self.logger.info(f"进度: {idx}/{len(stocks)} ({progress:.1f}%)")
                    
                    if progress_callback:
                        progress_callback(
                            progress,
                            f"正在更新... {idx}/{len(stocks)} ({progress:.1f}%)"
                        )
                
            except Exception as e:
                self.logger.error(f"更新 {code} 失败: {e}")
                fail_count += 1
                market_stats[market]['failed'] += 1
                failed_stocks.append({
                    'code': code,
                    'name': name,
                    'market': market,
                    'security_type': security_type,
                    'reason': str(e),
                })
                if progress_callback:
                    progress_callback(
                        (idx / len(stocks)) * 100,
                        f"[{market}] 更新 {code} 失败",
                        stock_code=code,
                        stock_name=name,
                        market=market,
                        security_type=security_type,
                        success=False,
                        records=0,
                        start_date=start_date,
                        end_date=end_date,
                        error=str(e),
                    )
        
        # 完成统计
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        self.logger.info("=" * 60)
        self.logger.info("增量更新完成")
        self.logger.info(f"总股票数: {len(stocks)}")
        self.logger.info(f"成功: {success_count}")
        self.logger.info(f"失败: {fail_count}")
        self.logger.info(f"总记录数: {total_records}")
        self.logger.info(f"分市场统计: {market_stats}")
        self.logger.info(f"耗时: {duration/60:.2f}分钟")
        self.logger.info("=" * 60)
        
        if progress_callback:
            progress_callback(100, f"更新完成！成功 {success_count} 只，失败 {fail_count} 只")

        market_errors = self._market_errors(market_stats)
        
        return {
            'success': not market_errors,
            'total_stocks': len(stocks),
            'success_count': success_count,
            'fail_count': fail_count,
            'total_records': total_records,
            'duration': duration,
            'failed_stocks': failed_stocks,
            'date_range': f"{start_date} 至 {end_date}",
            'markets': requested_markets,
            'market_stats': market_stats,
            'market_errors': market_errors,
        }
    
    def _resolve_security(
        self,
        session,
        code: str,
        market: str = 'CN',
        security_type: str = 'STOCK',
        security_id: int = None,
    ):
        if security_id is not None:
            stock = session.query(Stock).filter(
                Stock.id == security_id
            ).first()
        else:
            stock = session.query(Stock).filter(
                Stock.market == normalize_market(market),
                Stock.code == code,
                Stock.security_type == str(
                    security_type or 'STOCK'
                ).upper(),
            ).first()
        if not stock:
            raise ValueError(
                f"证券目录中不存在 {market}/{security_type}:{code}"
            )
        return stock

    def get_stock_data(
        self,
        code: str,
        start_date: str = None,
        end_date: str = None,
        limit: int = None,
        market: str = 'CN',
        security_type: str = 'STOCK',
        security_id: int = None,
    ) -> pd.DataFrame:
        """
        查询股票历史行情数据
        
        Args:
            code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            limit: 返回记录数限制（返回最新的N条数据）
            
        Returns:
            行情数据DataFrame（按日期升序排列，从旧到新）
        """
        session = self.Session()
        try:
            stock = self._resolve_security(
                session,
                code,
                market,
                security_type,
                security_id,
            )
            query = session.query(DailyMarket).filter(
                DailyMarket.security_id == stock.id
            )
            
            if start_date:
                query = query.filter(DailyMarket.trade_date >= start_date)
            
            if end_date:
                query = query.filter(DailyMarket.trade_date <= end_date)
            
            if limit:
                results = list(reversed(
                    query.order_by(DailyMarket.trade_date.desc())
                    .limit(limit)
                    .all()
                ))
            else:
                results = query.order_by(
                    DailyMarket.trade_date.asc()
                ).all()
            
            # 转换为DataFrame
            data = []
            for row in results:
                data.append({
                    'code': row.code,
                    'security_id': row.security_id,
                    'market': stock.market,
                    'security_type': stock.security_type,
                    'trade_date': row.trade_date,
                    'open': float(row.open) if row.open else None,
                    'close': float(row.close) if row.close else None,
                    'high': float(row.high) if row.high else None,
                    'low': float(row.low) if row.low else None,
                    'volume': int(row.volume) if row.volume else None,
                    'amount': float(row.amount) if row.amount else None,
                    'change_pct': float(row.change_pct) if row.change_pct else None,
                    'turnover_rate': float(row.turnover_rate) if row.turnover_rate else None,
                    'created_at': row.created_at
                })
            
            return pd.DataFrame(data)
        finally:
            session.close()

    def _fetch_security_daily_data(
        self,
        security: Dict[str, Any],
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """按市场与证券类型从上游读取日线，供批量导入和更新使用。"""
        market = str(security.get('market') or 'CN').upper()
        security_type = str(
            security.get('security_type') or 'STOCK'
        ).upper()
        code = security['code']

        # A 股股票继续走用户配置的数据源（AkShare/Tushare）。
        if market == 'CN' and security_type == 'STOCK':
            return self.datasource.get_daily_data(
                code, start_date, end_date
            )

        if self._security_market_router is None:
            from app.services.security_market_data_service import (
                SecurityMarketDataService,
            )
            self._security_market_router = SecurityMarketDataService(
                market_data_service=self,
            )
        return self._security_market_router.get_daily_data(
            code,
            market=market,
            security_type=security_type,
            start_date=start_date,
            end_date=end_date,
        )
    
    def get_latest_data(
        self,
        code: str,
        market: str = 'CN',
        security_type: str = 'STOCK',
    ) -> Optional[Dict[str, Any]]:
        """
        获取股票最新的行情数据
        
        Args:
            code: 股票代码
            
        Returns:
            最新行情数据字典
        """
        df = self.get_stock_data(
            code,
            limit=1,
            market=market,
            security_type=security_type,
        )
        if not df.empty:
            return df.iloc[0].to_dict()
        return None
    
    def get_data_date_range(
        self,
        code: str,
        market: str = 'CN',
        security_type: str = 'STOCK',
    ) -> Optional[Dict[str, str]]:
        """
        获取股票数据的日期范围
        
        Args:
            code: 股票代码
            
        Returns:
            包含最早和最晚日期的字典
        """
        session = self.Session()
        try:
            stock = self._resolve_security(
                session,
                code,
                market,
                security_type,
            )
            result = session.query(
                func.min(DailyMarket.trade_date).label('earliest_date'),
                func.max(DailyMarket.trade_date).label('latest_date'),
                func.count(DailyMarket.trade_date).label('record_count')
            ).filter(DailyMarket.security_id == stock.id).first()
            
            if result and result.earliest_date:
                return {
                    'earliest_date': str(result.earliest_date),
                    'latest_date': str(result.latest_date),
                    'record_count': int(result.record_count)
                }
            return None
        finally:
            session.close()
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取行情数据统计信息
        
        Returns:
            统计信息字典
        """
        session = self.Session()
        try:
            # 总记录数
            total_records = session.query(DailyMarket).count()
            
            directory_count = session.query(func.count(Stock.id)).scalar() or 0
            directory_by_market = {
                market: int(count)
                for market, count in (
                    session.query(Stock.market, func.count(Stock.id))
                    .group_by(Stock.market)
                    .all()
                )
            }

            # 先把 400 万级行情表压缩成数千个 security_id，再关联证券目录。
            # 直接关联 daily_market 后再 COUNT(DISTINCT ...) 会让 MySQL 扫描并
            # 分组全部行情记录，生产库一次需要约 8 秒，超过 Web 层超时。
            covered_securities = (
                session.query(DailyMarket.security_id.label('security_id'))
                .distinct()
                .subquery()
            )
            market_data_by_market = {
                market: int(count)
                for market, count in (
                    session.query(
                        Stock.market,
                        func.count(covered_securities.c.security_id),
                    )
                    .join(
                        covered_securities,
                        covered_securities.c.security_id == Stock.id,
                    )
                    .group_by(Stock.market)
                    .all()
                )
            }
            market_data_security_count = sum(
                market_data_by_market.values()
            )
            
            # 日期范围
            date_result = session.query(
                func.min(DailyMarket.trade_date).label('earliest_date'),
                func.max(DailyMarket.trade_date).label('latest_date')
            ).first()
            
            result = {
                'total_records': int(total_records),
                # 保留旧字段语义，避免破坏已有 API 使用方。
                'stock_count': int(market_data_security_count),
                'directory_count': int(directory_count),
                'market_data_security_count': int(
                    market_data_security_count
                ),
                'directory_by_market': directory_by_market,
                'market_data_by_market': market_data_by_market,
                'earliest_date': None,
                'latest_date': None
            }
            
            if date_result and date_result.earliest_date:
                result['earliest_date'] = str(date_result.earliest_date)
                result['latest_date'] = str(date_result.latest_date)
            
            return result
        finally:
            session.close()
    
    def get_stocks_with_data(self, limit: Optional[int] = None) -> List[str]:
        """
        获取有行情数据的股票代码列表
        
        Args:
            limit: 限制返回的股票数量
            
        Returns:
            股票代码列表
        """
        session = self.Session()
        try:
            query = session.query(DailyMarket.code).distinct().order_by(
                DailyMarket.code
            )
            
            if limit:
                query = query.limit(limit)
            
            result = query.all()
            stock_codes = [row[0] for row in result]
            
            return stock_codes
        finally:
            session.close()

    def get_securities_with_data(
        self,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        session = self.Session()
        try:
            query = (
                session.query(Stock)
                .join(
                    DailyMarket,
                    DailyMarket.security_id == Stock.id,
                )
                .filter(Stock.status == 'normal')
                .distinct()
                .order_by(Stock.id)
            )
            if limit:
                query = query.limit(limit)
            return [
                {
                    'security_id': stock.id,
                    'stock_code': stock.code,
                    'stock_name': stock.name,
                    'market': stock.market,
                    'security_type': stock.security_type,
                }
                for stock in query.all()
            ]
        finally:
            session.close()
    
    def get_data_statistics(self) -> Optional[Dict[str, Any]]:
        """
        获取数据统计信息（用于API和健康检查）
        
        Returns:
            统计信息字典，包含：stock_count, total_records, min_date, max_date
        """
        stats = self.get_statistics()
        
        # 转换字段名以匹配API期望
        return {
            'stock_count': stats.get('stock_count', 0),
            'directory_count': stats.get('directory_count', 0),
            'market_data_security_count': stats.get(
                'market_data_security_count',
                stats.get('stock_count', 0),
            ),
            'directory_by_market': stats.get('directory_by_market', {}),
            'market_data_by_market': stats.get(
                'market_data_by_market',
                {},
            ),
            'total_records': stats.get('total_records', 0),
            'min_date': stats.get('earliest_date'),
            'max_date': stats.get('latest_date')
        }
    
    def _save_daily_data(
        self,
        df: pd.DataFrame,
        code: str,
        update_date_range: bool = False,
        security_id: int = None,
    ):
        """
        保存日线数据到MySQL
        
        Args:
            df: 行情数据DataFrame
            code: 股票代码
            update_date_range: 是否更新 stocks 表的日期字段
        """
        if df.empty:
            return
        
        session = self.Session()
        try:
            first = df.iloc[0]
            stock = self._resolve_security(
                session,
                code,
                str(first.get('market') or 'CN'),
                str(first.get('security_type') or 'STOCK'),
                security_id,
            )
            security_id = stock.id

            # 确保有code列
            if 'code' not in df.columns:
                df['code'] = code
            
            # 遍历DataFrame，逐条插入或更新
            for _, row in df.iterrows():
                values = {
                    column: self._database_value(row.get(column))
                    for column in (
                        'open', 'close', 'high', 'low', 'volume',
                        'amount', 'change_pct', 'turnover_rate',
                    )
                }
                row_code = self._database_value(row.get('code')) or code
                trade_date = self._database_value(row.get('trade_date'))
                if not row_code or trade_date is None:
                    raise ValueError("行情记录缺少证券代码或交易日期")

                # 检查记录是否已存在
                exists = session.query(DailyMarket).filter(
                    DailyMarket.security_id == security_id,
                    DailyMarket.trade_date == trade_date
                ).first()
                
                if exists:
                    # 更新现有记录
                    exists.open = values['open']
                    exists.close = values['close']
                    exists.high = values['high']
                    exists.low = values['low']
                    exists.volume = values['volume']
                    exists.amount = values['amount']
                    exists.change_pct = values['change_pct']
                    exists.turnover_rate = values['turnover_rate']
                else:
                    # 创建新记录
                    daily_market = DailyMarket(
                        security_id=security_id,
                        code=row_code,
                        trade_date=trade_date,
                        open=values['open'],
                        close=values['close'],
                        high=values['high'],
                        low=values['low'],
                        volume=values['volume'],
                        amount=values['amount'],
                        change_pct=values['change_pct'],
                        turnover_rate=values['turnover_rate'],
                        created_at=(
                            self._database_value(row.get('created_at'))
                            or datetime.now()
                        )
                    )
                    session.add(daily_market)
            
            session.commit()
            
            # 如果需要更新日期字段
            if update_date_range:
                try:
                    # 提取 DataFrame 中的交易日期
                    dates = df['trade_date'].tolist()
                    
                    if dates:
                        # 转换日期格式（如果需要）
                        from datetime import date as DateType
                        date_objects = []
                        for d in dates:
                            if isinstance(d, str):
                                date_objects.append(datetime.strptime(d, '%Y-%m-%d').date())
                            elif isinstance(d, datetime):
                                date_objects.append(d.date())
                            elif isinstance(d, DateType):
                                date_objects.append(d)
                            else:
                                date_objects.append(d)
                        
                        # 计算最小和最大日期
                        earliest_date = min(date_objects)
                        latest_date = max(date_objects)
                        
                        # 使用日期范围服务更新 stocks 表
                        success = self.date_range_service.update_stock_date_range(
                            code,
                            earliest_date=earliest_date,
                            latest_date=latest_date,
                            security_id=security_id,
                        )
                        
                        if success:
                            self.logger.debug(f"更新股票{code}的日期范围: {earliest_date} ~ {latest_date}")
                        else:
                            self.logger.warning(f"更新股票{code}的日期范围失败")
                
                except Exception as e:
                    # 日期字段更新失败不应影响主流程
                    self.logger.error(f"更新股票{code}的日期范围时发生错误: {e}", exc_info=True)
        
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()

    @staticmethod
    def _database_value(value):
        """把 pandas/numpy 缺失值转换为 MySQL 可接受的 NULL。"""
        if value is None:
            return None
        try:
            if bool(pd.isna(value)):
                return None
        except (TypeError, ValueError):
            pass
        if hasattr(value, 'item'):
            value = value.item()
        if isinstance(value, numbers.Real) and not math.isfinite(float(value)):
            return None
        return value
    
    def _delete_data_in_range(
        self,
        security_id: int,
        start_date: str,
        end_date: str,
    ):
        """
        删除指定日期范围内的数据
        
        Args:
            code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
        """
        session = self.Session()
        try:
            deleted_count = session.query(DailyMarket).filter(
                DailyMarket.security_id == security_id,
                DailyMarket.trade_date >= start_date,
                DailyMarket.trade_date <= end_date
            ).delete()
            session.commit()
            self.logger.debug(
                f"删除了 {deleted_count} 条记录: "
                f"security_id={security_id} {start_date}~{end_date}"
            )
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    def incremental_update(
        self,
        force_full_update: bool = False,
        markets=None,
        progress_callback: Callable = None,
        stop_event=None,
    ) -> Dict[str, Any]:
        """智能增量更新股票数据，根据每只股票的最新数据日期只下载缺失的数据"""
        self.logger.info("=" * 60)
        self.logger.info(f"开始{'全量' if force_full_update else '智能增量'}更新股票数据")
        self.logger.info("=" * 60)
        
        start_time = datetime.now()
        current_date = date.today()
        
        if stop_event and stop_event.is_set():
            return {'success': False, 'message': '任务已取消', 'cancelled': True}
        
        stocks, requested_markets = self._load_market_securities(
            markets=markets,
        )
        total_stocks = len(stocks)
        market_stats = self._build_market_stats(
            stocks,
            requested_markets,
        )
        
        self.logger.info(
            "证券总数: %s，覆盖市场: %s",
            total_stocks,
            ', '.join(requested_markets),
        )
        if progress_callback:
            progress_callback(
                0,
                f"准备更新 {total_stocks} 只证券，覆盖 "
                f"{'/'.join(requested_markets)}",
            )
        
        success_count = fail_count = skipped_count = total_records = 0
        failed_stocks = []
        skipped_stocks = []
        
        for idx, stock in enumerate(stocks, 1):
            if stop_event and stop_event.is_set():
                return {
                    'success': False, 'message': '任务已取消', 'cancelled': True,
                    'success_count': success_count, 'fail_count': fail_count,
                    'skipped_count': skipped_count, 'total_records': total_records,
                    'failed_stocks': failed_stocks,
                    'skipped_stocks': skipped_stocks,
                    'markets': requested_markets,
                    'market_stats': market_stats,
                }
            
            code = stock['code']
            security_id = stock['id']
            name = stock['name']
            market = stock['market']
            security_type = stock['security_type']
            
            try:
                if force_full_update:
                    needs_update = True
                    update_reason = "强制全量更新"
                    start_date_str = (current_date - timedelta(days=365*3)).strftime('%Y-%m-%d')
                else:
                    needs_update, reason = self.date_range_service.needs_update(
                        code,
                        current_date,
                        security_id=security_id,
                    )
                    
                    if not needs_update:
                        skipped_count += 1
                        market_stats[market]['skipped'] += 1
                        skipped_stocks.append({
                            'code': code,
                            'name': name,
                            'market': market,
                            'security_type': security_type,
                            'reason': reason,
                        })
                        self.logger.debug(f"[{idx}/{len(stocks)}] 跳过 {code} - {name}: {reason}")
                        continue
                    
                    start_date_obj = (
                        self.date_range_service.calculate_update_start_date(
                            code,
                            current_date,
                            security_id=security_id,
                        )
                    )
                    if start_date_obj:
                        start_date_str = start_date_obj.strftime('%Y-%m-%d')
                        update_reason = reason
                    else:
                        skipped_count += 1
                        market_stats[market]['skipped'] += 1
                        skipped_stocks.append({
                            'code': code,
                            'name': name,
                            'market': market,
                            'security_type': security_type,
                            'reason': '无法计算起始日期',
                        })
                        continue
                
                end_date_str = current_date.strftime('%Y-%m-%d')
                market_stats[market]['attempted'] += 1
                self.logger.info(
                    f"[{idx}/{len(stocks)}][{market}/{security_type}] "
                    f"更新 {code} - {name}: {start_date_str} ~ "
                    f"{end_date_str} ({update_reason})"
                )
                
                self.rate_limiter.wait()
                df = self._fetch_security_daily_data(
                    stock, start_date_str, end_date_str
                )
                
                if df.empty:
                    self.logger.debug(f"  {code} 无新数据")
                    skipped_count += 1
                    market_stats[market]['skipped'] += 1
                    skipped_stocks.append({
                        'code': code,
                        'name': name,
                        'market': market,
                        'security_type': security_type,
                        'reason': '无新数据',
                    })
                    continue
                
                records = len(df)
                self._save_daily_data(
                    df,
                    code,
                    update_date_range=True,
                    security_id=security_id,
                )
                
                success_count += 1
                total_records += records
                market_stats[market]['success'] += 1
                market_stats[market]['records'] += records
                self.logger.info(f"  ✓ {code} 更新成功，{records}条记录")
                
                if progress_callback:
                    progress_callback(
                        (idx / len(stocks)) * 100,
                        f"更新 {code} 成功",
                        stock_code=code,
                        stock_name=name,
                        market=market,
                        security_type=security_type,
                        success=True,
                        records=records,
                        update_type='full' if force_full_update else 'incremental',
                        start_date=start_date_str,
                        end_date=end_date_str
                    )
                
                if idx % 10 == 0:
                    elapsed = (datetime.now() - start_time).total_seconds()
                    avg_time = elapsed / idx
                    remaining = avg_time * (len(stocks) - idx)
                    progress = (idx / len(stocks)) * 100
                    
                    self.logger.info(f"进度: {idx}/{len(stocks)} ({progress:.1f}%), 成功: {success_count}, 跳过: {skipped_count}")
                    
                    if progress_callback:
                        progress_callback(progress, f"正在更新... {idx}/{len(stocks)} ({progress:.1f}%), 成功: {success_count}, 跳过: {skipped_count}")
            
            except Exception as e:
                self.logger.error(f"  ✗ {code} 更新失败: {e}")
                fail_count += 1
                market_stats[market]['failed'] += 1
                failed_stocks.append({
                    'code': code,
                    'name': name,
                    'market': market,
                    'security_type': security_type,
                    'reason': str(e),
                })
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        self.logger.info("=" * 60)
        self.logger.info(f"{'全量' if force_full_update else '智能增量'}更新完成")
        self.logger.info(f"总股票数: {len(stocks)}, 成功: {success_count}, 跳过: {skipped_count}, 失败: {fail_count}")
        self.logger.info(f"总记录数: {total_records}, 耗时: {duration/60:.2f}分钟")
        self.logger.info(f"分市场统计: {market_stats}")
        self.logger.info("=" * 60)
        
        if progress_callback:
            progress_callback(100, f"更新完成！成功 {success_count} 只，跳过 {skipped_count} 只，失败 {fail_count} 只，共 {total_records} 条记录")
        
        market_errors = self._market_errors(market_stats)

        return {
            'success': not market_errors,
            'total_stocks': len(stocks), 'success_count': success_count,
            'fail_count': fail_count, 'skipped_count': skipped_count,
            'total_records': total_records, 'duration': duration,
            'failed_stocks': failed_stocks, 'skipped_stocks': skipped_stocks,
            'update_type': 'full' if force_full_update else 'incremental',
            'markets': requested_markets,
            'market_stats': market_stats,
            'market_errors': market_errors,
        }


# 全局服务实例
_market_data_service_instance: Optional[MarketDataService] = None


def get_market_data_service() -> MarketDataService:
    """
    获取全局行情数据服务实例
    
    Returns:
        MarketDataService实例
    """
    global _market_data_service_instance
    if _market_data_service_instance is None:
        _market_data_service_instance = MarketDataService()
    return _market_data_service_instance
