"""
历史行情数据管理服务
负责股票历史行情数据的获取、存储和查询
"""
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime, timedelta, date
import pandas as pd
from app.models.orm_models import DailyMarket, ORMDatabase
from app.models.mysql_db import MySQLDatabase
from app.services import get_datasource, get_stock_service, get_stock_date_range_service
from app.services.stock_date_range_service import StockDateRangeService
from app.utils import get_logger, get_rate_limiter, get_config, get_stock_limit_for_mode
from sqlalchemy import func
from sqlalchemy.orm import sessionmaker

logger = get_logger(__name__)


class MarketDataService:
    """历史行情数据管理服务类"""
    
    def __init__(self):
        """初始化行情数据服务"""
        self.datasource = get_datasource()
        self.stock_service = get_stock_service()
        self.rate_limiter = get_rate_limiter()
        self.config = get_config()
        
        # 创建ORM数据库连接
        mysql_config = self.config.get('database.mysql')
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
        
        # 创建日期范围服务
        mysql_db = MySQLDatabase()
        self.date_range_service = StockDateRangeService(mysql_db)
        
        logger.info("行情数据服务初始化完成")
    
    def import_all_history(self, start_date: str = None, end_date: str = None,
                          limit: int = None, skip: int = 0, 
                          progress_callback: Callable = None,
                          stop_event = None) -> Dict[str, Any]:
        """
        全量导入所有股票的历史行情数据
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)，默认为3年前
            end_date: 结束日期 (YYYY-MM-DD)，默认为今天
            limit: 限制导入的股票数量（用于测试），如果为None则根据配置自动确定
            skip: 跳过前N只股票
            progress_callback: 进度回调函数 callback(progress: float, message: str)
            stop_event: 停止事件，用于取消任务
            
        Returns:
            包含执行结果的字典
        """
        logger.info("=" * 60)
        logger.info("开始全量导入历史行情数据")
        logger.info("=" * 60)
        
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
        
        logger.info(f"日期范围: {start_date} 至 {end_date}")
        
        if progress_callback:
            progress_callback(0, f"准备导入数据，日期范围：{start_date} 至 {end_date}")
        
        # 获取所有股票列表
        stocks = self.stock_service.get_stock_list()
        total_stocks = len(stocks)
        
        # 应用skip和limit
        if skip > 0:
            stocks = stocks[skip:]
            logger.info(f"跳过前{skip}只股票")
        
        # 如果没有显式指定limit，则根据配置自动应用限制
        if limit is None:
            limit = get_stock_limit_for_mode()
            if limit:
                logger.info(f"开发模式：限制导入{limit}只股票")
        
        if limit:
            stocks = stocks[:limit]
            logger.info(f"限制导入{limit}只股票（测试模式）")
        
        logger.info(f"待导入股票数量: {len(stocks)}/{total_stocks}")
        
        if progress_callback:
            progress_callback(1, f"待导入 {len(stocks)} 只股票")
        
        # 统计信息
        success_count = 0
        fail_count = 0
        total_records = 0
        failed_stocks = []
        
        # 逐个股票导入
        for idx, stock in enumerate(stocks, 1):
            # 检查是否已取消
            if stop_event and stop_event.is_set():
                logger.warning(f"任务被取消，停止导入。已完成 {idx-1}/{len(stocks)} 只股票")
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
                    'date_range': f"{start_date} 至 {end_date}"
                }
            
            code = stock['code']
            name = stock['name']
            
            try:
                logger.info(f"[{idx}/{len(stocks)}] 正在导入 {code} - {name}")
                
                # API频率控制
                self.rate_limiter.wait()
                
                # 获取历史行情数据
                df = self.datasource.get_daily_data(code, start_date, end_date)
                
                if df.empty:
                    logger.warning(f"  {code} 未获取到数据")
                    fail_count += 1
                    failed_stocks.append({'code': code, 'name': name, 'reason': '未获取到数据'})
                    
                    # 记录失败的详细信息
                    if progress_callback:
                        progress_callback(
                            (idx / len(stocks)) * 100,
                            f"导入 {code} 失败",
                            stock_code=code,
                            stock_name=name,
                            success=False,
                            records=0,
                            start_date=start_date,
                            end_date=end_date,
                            error='未获取到数据'
                        )
                    continue
                
                # 保存到DuckDB
                records = len(df)
                self._save_daily_data(df, code)
                
                success_count += 1
                total_records += records
                logger.info(f"  ✓ {code} 导入成功，{records}条记录")
                
                # 记录成功的详细信息
                if progress_callback:
                    progress_callback(
                        (idx / len(stocks)) * 100,
                        f"导入 {code} 成功",
                        stock_code=code,
                        stock_name=name,
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
                    
                    logger.info(f"进度: {idx}/{len(stocks)} ({progress:.1f}%), "
                              f"预计剩余时间: {remaining/60:.1f}分钟")
                    
                    if progress_callback:
                        progress_callback(
                            progress, 
                            f"正在导入... {idx}/{len(stocks)} ({progress:.1f}%), "
                            f"预计剩余 {remaining/60:.1f} 分钟"
                        )
                
            except Exception as e:
                logger.error(f"  ✗ {code} 导入失败: {e}")
                fail_count += 1
                failed_stocks.append({'code': code, 'name': name, 'reason': str(e)})
                
                # 记录失败的详细信息
                if progress_callback:
                    progress_callback(
                        (idx / len(stocks)) * 100,
                        f"导入 {code} 失败",
                        stock_code=code,
                        stock_name=name,
                        success=False,
                        records=0,
                        start_date=start_date,
                        end_date=end_date,
                        error=str(e)
                    )
        
        # 完成统计
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info("=" * 60)
        logger.info("全量导入完成")
        logger.info(f"总股票数: {len(stocks)}")
        logger.info(f"成功: {success_count}")
        logger.info(f"失败: {fail_count}")
        logger.info(f"总记录数: {total_records}")
        logger.info(f"耗时: {duration/60:.2f}分钟")
        logger.info("=" * 60)
        
        if failed_stocks:
            logger.warning(f"失败的股票列表（前10个）:")
            for stock in failed_stocks[:10]:
                logger.warning(f"  {stock['code']} - {stock['name']}: {stock['reason']}")
        
        if progress_callback:
            progress_callback(100, f"导入完成！成功 {success_count} 只，失败 {fail_count} 只，共 {total_records} 条记录")
        
        return {
            'success': True,
            'total_stocks': len(stocks),
            'success_count': success_count,
            'fail_count': fail_count,
            'total_records': total_records,
            'duration': duration,
            'failed_stocks': failed_stocks,
            'date_range': f"{start_date} 至 {end_date}"
        }
    
    def update_recent_data(self, days: int = 5, only_existing: bool = True, 
                          progress_callback: Callable = None,
                          stop_event = None) -> Dict[str, Any]:
        """
        增量更新最近N天的行情数据
        
        Args:
            days: 更新最近N天的数据
            only_existing: 是否只更新已有数据的股票（默认True）
            progress_callback: 进度回调函数 callback(progress: float, message: str)
            stop_event: 停止事件，用于取消任务
            
        Returns:
            包含执行结果的字典
        """
        logger.info("=" * 60)
        logger.info(f"开始增量更新最近{days}天的行情数据")
        logger.info("=" * 60)
        
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
        
        logger.info(f"日期范围: {start_date} 至 {end_date}")
        
        if progress_callback:
            progress_callback(0, f"准备更新数据，日期范围：{start_date} 至 {end_date}")
        
        # 获取需要更新的股票列表
        if only_existing:
            # 只更新已有数据的股票
            session = self.Session()
            try:
                result = session.query(DailyMarket.code).distinct().all()
                stock_codes = [row[0] for row in result]
                
                # 从股票服务获取完整信息
                all_stocks = self.stock_service.get_stock_list()
                stocks = [s for s in all_stocks if s['code'] in stock_codes]
                logger.info(f"只更新已有数据的股票: {len(stocks)}只")
            finally:
                session.close()
        else:
            # 更新所有股票
            stocks = self.stock_service.get_stock_list()
            logger.info(f"更新所有股票: {len(stocks)}只")
        
        logger.info(f"待更新股票数量: {len(stocks)}")
        
        if progress_callback:
            progress_callback(1, f"待更新 {len(stocks)} 只股票")
        
        # 统计信息
        success_count = 0
        fail_count = 0
        total_records = 0
        failed_stocks = []
        
        # 逐个股票更新
        for idx, stock in enumerate(stocks, 1):
            # 检查是否已取消
            if stop_event and stop_event.is_set():
                logger.warning(f"任务被取消，停止更新。已完成 {idx-1}/{len(stocks)} 只股票")
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
                    'date_range': f"{start_date} 至 {end_date}"
                }
            
            code = stock['code']
            name = stock['name']
            
            try:
                # API频率控制
                self.rate_limiter.wait()
                
                # 获取最近的行情数据
                df = self.datasource.get_daily_data(code, start_date, end_date)
                
                if df.empty:
                    fail_count += 1
                    continue
                
                # 删除该股票在日期范围内的旧数据
                self._delete_data_in_range(code, start_date, end_date)
                
                # 保存新数据
                records = len(df)
                self._save_daily_data(df, code)
                
                success_count += 1
                total_records += records
                
                # 每10只股票显示一次进度
                if idx % 10 == 0:
                    progress = (idx / len(stocks)) * 100
                    logger.info(f"进度: {idx}/{len(stocks)} ({progress:.1f}%)")
                    
                    if progress_callback:
                        progress_callback(
                            progress,
                            f"正在更新... {idx}/{len(stocks)} ({progress:.1f}%)"
                        )
                
            except Exception as e:
                logger.error(f"更新 {code} 失败: {e}")
                fail_count += 1
                failed_stocks.append({'code': code, 'name': name, 'reason': str(e)})
        
        # 完成统计
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info("=" * 60)
        logger.info("增量更新完成")
        logger.info(f"总股票数: {len(stocks)}")
        logger.info(f"成功: {success_count}")
        logger.info(f"失败: {fail_count}")
        logger.info(f"总记录数: {total_records}")
        logger.info(f"耗时: {duration/60:.2f}分钟")
        logger.info("=" * 60)
        
        if progress_callback:
            progress_callback(100, f"更新完成！成功 {success_count} 只，失败 {fail_count} 只")
        
        return {
            'success': True,
            'total_stocks': len(stocks),
            'success_count': success_count,
            'fail_count': fail_count,
            'total_records': total_records,
            'duration': duration,
            'failed_stocks': failed_stocks,
            'date_range': f"{start_date} 至 {end_date}"
        }
    
    def get_stock_data(self, code: str, start_date: str = None, 
                      end_date: str = None, limit: int = None) -> pd.DataFrame:
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
            query = session.query(DailyMarket).filter(DailyMarket.code == code)
            
            if start_date:
                query = query.filter(DailyMarket.trade_date >= start_date)
            
            if end_date:
                query = query.filter(DailyMarket.trade_date <= end_date)
            
            # 如果有limit限制，需要先获取最新的N条记录
            if limit:
                # 使用子查询：先按日期降序排序取最新的N条，再按日期升序排序返回
                subq = session.query(DailyMarket.code, DailyMarket.trade_date) \
                    .filter(DailyMarket.code == code)
                
                # 应用start_date和end_date过滤条件
                if start_date:
                    subq = subq.filter(DailyMarket.trade_date >= start_date)
                if end_date:
                    subq = subq.filter(DailyMarket.trade_date <= end_date)
                
                # 按日期降序排序，取最新的N条
                subq = subq.order_by(DailyMarket.trade_date.desc()).limit(limit).subquery()
                
                # 查询最新的N条记录，并按日期升序排序返回
                query = session.query(DailyMarket) \
                    .join(subq, (DailyMarket.code == subq.c.code) & (DailyMarket.trade_date == subq.c.trade_date)) \
                    .order_by(DailyMarket.trade_date.asc())
            else:
                # 没有limit限制，按日期升序排列（从旧到新）
                query = query.order_by(DailyMarket.trade_date.asc())
            
            results = query.all()
            
            # 转换为DataFrame
            data = []
            for row in results:
                data.append({
                    'code': row.code,
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
    
    def get_latest_data(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取股票最新的行情数据
        
        Args:
            code: 股票代码
            
        Returns:
            最新行情数据字典
        """
        df = self.get_stock_data(code, limit=1)
        if not df.empty:
            return df.iloc[0].to_dict()
        return None
    
    def get_data_date_range(self, code: str) -> Optional[Dict[str, str]]:
        """
        获取股票数据的日期范围
        
        Args:
            code: 股票代码
            
        Returns:
            包含最早和最晚日期的字典
        """
        session = self.Session()
        try:
            result = session.query(
                func.min(DailyMarket.trade_date).label('earliest_date'),
                func.max(DailyMarket.trade_date).label('latest_date'),
                func.count(DailyMarket.trade_date).label('record_count')
            ).filter(DailyMarket.code == code).first()
            
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
            
            # 股票数量
            stock_count = session.query(DailyMarket.code).distinct().count()
            
            # 日期范围
            date_result = session.query(
                func.min(DailyMarket.trade_date).label('earliest_date'),
                func.max(DailyMarket.trade_date).label('latest_date')
            ).first()
            
            result = {
                'total_records': int(total_records),
                'stock_count': int(stock_count),
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
            query = session.query(DailyMarket.code).distinct().order_by(DailyMarket.code)
            
            if limit:
                query = query.limit(limit)
            
            result = query.all()
            stock_codes = [row[0] for row in result]
            
            return stock_codes
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
            'total_records': stats.get('total_records', 0),
            'min_date': stats.get('earliest_date'),
            'max_date': stats.get('latest_date')
        }
    
    def _save_daily_data(self, df: pd.DataFrame, code: str):
        """
        保存日线数据到MySQL
        
        Args:
            df: 行情数据DataFrame
            code: 股票代码
        """
        if df.empty:
            return
        
        session = self.Session()
        try:
            # 确保有code列
            if 'code' not in df.columns:
                df['code'] = code
            
            # 遍历DataFrame，逐条插入或更新
            for _, row in df.iterrows():
                # 检查记录是否已存在
                exists = session.query(DailyMarket).filter(
                    DailyMarket.code == row['code'],
                    DailyMarket.trade_date == row['trade_date']
                ).first()
                
                if exists:
                    # 更新现有记录
                    exists.open = row.get('open')
                    exists.close = row.get('close')
                    exists.high = row.get('high')
                    exists.low = row.get('low')
                    exists.volume = row.get('volume')
                    exists.amount = row.get('amount')
                    exists.change_pct = row.get('change_pct')
                    exists.turnover_rate = row.get('turnover_rate')
                else:
                    # 创建新记录
                    daily_market = DailyMarket(
                        code=row['code'],
                        trade_date=row['trade_date'],
                        open=row.get('open'),
                        close=row.get('close'),
                        high=row.get('high'),
                        low=row.get('low'),
                        volume=row.get('volume'),
                        amount=row.get('amount'),
                        change_pct=row.get('change_pct'),
                        turnover_rate=row.get('turnover_rate'),
                        created_at=row.get('created_at', datetime.now())
                    )
                    session.add(daily_market)
            
            session.commit()
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    def _delete_data_in_range(self, code: str, start_date: str, end_date: str):
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
                DailyMarket.code == code,
                DailyMarket.trade_date >= start_date,
                DailyMarket.trade_date <= end_date
            ).delete()
            session.commit()
            logger.debug(f"删除了 {deleted_count} 条记录: {code} {start_date}~{end_date}")
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    def incremental_update(self, force_full_update: bool = False, progress_callback: Callable = None, stop_event = None) -> Dict[str, Any]:
        """智能增量更新股票数据，根据每只股票的最新数据日期只下载缺失的数据"""
        logger.info("=" * 60)
        logger.info(f"开始{'全量' if force_full_update else '智能增量'}更新股票数据")
        logger.info("=" * 60)
        
        start_time = datetime.now()
        current_date = date.today()
        
        if stop_event and stop_event.is_set():
            return {'success': False, 'message': '任务已取消', 'cancelled': True}
        
        stocks = self.stock_service.get_stock_list()
        total_stocks = len(stocks)
        
        logger.info(f"股票总数: {total_stocks}")
        if progress_callback:
            progress_callback(0, f"准备更新 {total_stocks} 只股票")
        
        success_count = fail_count = skipped_count = total_records = 0
        failed_stocks = []
        skipped_stocks = []
        
        for idx, stock in enumerate(stocks, 1):
            if stop_event and stop_event.is_set():
                return {
                    'success': False, 'message': '任务已取消', 'cancelled': True,
                    'success_count': success_count, 'fail_count': fail_count,
                    'skipped_count': skipped_count, 'total_records': total_records,
                    'failed_stocks': failed_stocks, 'skipped_stocks': skipped_stocks
                }
            
            code = stock['code']
            name = stock['name']
            
            try:
                if force_full_update:
                    needs_update = True
                    update_reason = "强制全量更新"
                    start_date_str = (current_date - timedelta(days=365*3)).strftime('%Y-%m-%d')
                else:
                    needs_update, reason = self.date_range_service.needs_update(code, current_date)
                    
                    if not needs_update:
                        skipped_count += 1
                        skipped_stocks.append({'code': code, 'name': name, 'reason': reason})
                        logger.debug(f"[{idx}/{len(stocks)}] 跳过 {code} - {name}: {reason}")
                        continue
                    
                    start_date_obj = self.date_range_service.calculate_update_start_date(code, current_date)
                    if start_date_obj:
                        start_date_str = start_date_obj.strftime('%Y-%m-%d')
                        update_reason = reason
                    else:
                        skipped_count += 1
                        skipped_stocks.append({'code': code, 'name': name, 'reason': '无法计算起始日期'})
                        continue
                
                end_date_str = current_date.strftime('%Y-%m-%d')
                logger.info(f"[{idx}/{len(stocks)}] 更新 {code} - {name}: {start_date_str} ~ {end_date_str} ({update_reason})")
                
                self.rate_limiter.wait()
                df = self.datasource.get_daily_data(code, start_date_str, end_date_str)
                
                if df.empty:
                    logger.debug(f"  {code} 无新数据")
                    skipped_count += 1
                    skipped_stocks.append({'code': code, 'name': name, 'reason': '无新数据'})
                    continue
                
                records = len(df)
                self._save_daily_data(df, code, update_date_range=True)
                
                success_count += 1
                total_records += records
                logger.info(f"  ✓ {code} 更新成功，{records}条记录")
                
                if progress_callback:
                    progress_callback(
                        (idx / len(stocks)) * 100,
                        f"更新 {code} 成功",
                        stock_code=code,
                        stock_name=name,
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
                    
                    logger.info(f"进度: {idx}/{len(stocks)} ({progress:.1f}%), 成功: {success_count}, 跳过: {skipped_count}")
                    
                    if progress_callback:
                        progress_callback(progress, f"正在更新... {idx}/{len(stocks)} ({progress:.1f}%), 成功: {success_count}, 跳过: {skipped_count}")
            
            except Exception as e:
                logger.error(f"  ✗ {code} 更新失败: {e}")
                fail_count += 1
                failed_stocks.append({'code': code, 'name': name, 'reason': str(e)})
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info("=" * 60)
        logger.info(f"{'全量' if force_full_update else '智能增量'}更新完成")
        logger.info(f"总股票数: {len(stocks)}, 成功: {success_count}, 跳过: {skipped_count}, 失败: {fail_count}")
        logger.info(f"总记录数: {total_records}, 耗时: {duration/60:.2f}分钟")
        logger.info("=" * 60)
        
        if progress_callback:
            progress_callback(100, f"更新完成！成功 {success_count} 只，跳过 {skipped_count} 只，失败 {fail_count} 只，共 {total_records} 条记录")
        
        return {
            'success': True, 'total_stocks': len(stocks), 'success_count': success_count,
            'fail_count': fail_count, 'skipped_count': skipped_count,
            'total_records': total_records, 'duration': duration,
            'failed_stocks': failed_stocks, 'skipped_stocks': skipped_stocks,
            'update_type': 'full' if force_full_update else 'incremental'
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
