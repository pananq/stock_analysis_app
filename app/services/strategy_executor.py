"""
策略执行引擎

负责执行策略，扫描股票，查找符合条件的股票
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
import pandas as pd
from app.models.database_factory import get_database
from app.models import get_duckdb
from app.services.strategy_service import get_strategy_service
from app.services.market_data_service import get_market_data_service
from app.indicators import TechnicalIndicators
from app.utils import get_logger, get_stock_limit_for_mode

logger = get_logger(__name__)


class StrategyExecutor:
    """策略执行引擎"""
    
    def __init__(self):
        """初始化策略执行引擎"""
        self.db = get_database()  # 使用工厂方法获取数据库（MySQL或SQLite）
        self.duckdb = get_duckdb()  # DuckDB 用于行情数据
        self.strategy_service = get_strategy_service()
        self.market_data_service = get_market_data_service()
        self.indicators = TechnicalIndicators()
        logger.info("策略执行引擎初始化完成")
    
    def execute_strategy(self, strategy_id: int, 
                        start_date: Optional[str] = None,
                        end_date: Optional[str] = None,
                        limit_stocks: Optional[int] = None,
                        progress_callback: Optional[callable] = None,
                        stop_event: Optional[Any] = None) -> Dict[str, Any]:
        """
        执行策略
        
        Args:
            strategy_id: 策略ID
            start_date: 开始日期（格式：YYYY-MM-DD），默认为30天前
            end_date: 结束日期（格式：YYYY-MM-DD），默认为今天
            limit_stocks: 限制扫描的股票数量（用于测试），如果为None则根据配置自动确定
            progress_callback: 进度回调函数
            stop_event: 停止事件
            
        Returns:
            执行结果统计信息
        """
        try:
            # 初始化进度
            if progress_callback:
                progress_callback(0, '正在初始化...')
            # 获取策略配置
            strategy = self.strategy_service.get_strategy(strategy_id)
            if not strategy:
                logger.error(f"策略不存在: {strategy_id}")
                return {
                    'success': False,
                    'error': '策略不存在'
                }
            
            if not strategy['enabled']:
                logger.warning(f"策略未启用: {strategy['name']}")
                return {
                    'success': False,
                    'error': '策略未启用'
                }
            
            logger.info(f"开始执行策略: {strategy['name']} (ID: {strategy_id})")
            
            # 解析策略配置
            config = strategy['config']
            rise_threshold = config['rise_threshold']
            observation_days = config['observation_days']
            ma_period = config['ma_period']
            
            logger.info(f"策略参数: 涨幅阈值={rise_threshold}%, 观察天数={observation_days}, 均线周期={ma_period}日")
            
            # 设置日期范围
            if not end_date:
                end_date = datetime.now().strftime('%Y-%m-%d')
            
            if not start_date:
                # 默认扫描最近30天
                start_dt = datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=30)
                start_date = start_dt.strftime('%Y-%m-%d')
            
            logger.info(f"扫描日期范围: {start_date} 至 {end_date}")
            
            # 获取有行情数据的股票列表
            if progress_callback:
                progress_callback(5, '正在获取股票列表...')
            
            # 如果没有显式指定limit_stocks，则根据配置自动应用限制
            if limit_stocks is None:
                limit_stocks = get_stock_limit_for_mode()
                if limit_stocks:
                    logger.info(f"开发模式：限制扫描{limit_stocks}只股票")
            
            stocks = self._get_stocks_with_data(limit_stocks)
            logger.info(f"待扫描股票数量: {len(stocks)}")
            
            if not stocks:
                logger.warning("没有找到有行情数据的股票")
                if progress_callback:
                    progress_callback(100, '没有找到股票数据')
                return {
                    'success': True,
                    'strategy_id': strategy_id,
                    'strategy_name': strategy['name'],
                    'scanned_stocks': 0,
                'matched_count': 0,
                'saved_count': 0,
                'matches': [],
                'execution_time': 0
                }
            
            # 扫描股票
            matches = []
            scanned_count = 0
            total_stocks = len(stocks)
            start_time = datetime.now()
            
            for stock in stocks:
                # 检查是否需要停止
                if stop_event and stop_event.is_set():
                    logger.warning("策略执行被取消")
                    if progress_callback:
                        progress_callback(100, '任务已取消')
                    return {
                        'success': False,
                        'error': '任务已取消'
                    }
                
                stock_code = stock['stock_code']
                stock_name = stock['stock_name']
                
                try:
                    # 查找符合条件的交易日
                    stock_matches = self._scan_stock(
                        stock_code, stock_name,
                        start_date, end_date,
                        rise_threshold, observation_days, ma_period
                    )
                    
                    if stock_matches:
                        matches.extend(stock_matches)
                        # 提取所有匹配的日期
                        match_dates = [m['trigger_date'] for m in stock_matches]
                        dates_str = ', '.join(match_dates)
                        logger.info(f"  {stock_code} {stock_name}: 找到 {len(stock_matches)} 个匹配，日期: {dates_str}")
                    
                    scanned_count += 1
                    
                    # 更新进度
                    if progress_callback and scanned_count % 10 == 0:
                        progress = 10 + (scanned_count / total_stocks * 80)  # 10%-90%
                        progress_callback(
                            progress,
                            f'正在扫描股票 {scanned_count}/{total_stocks}，已找到 {len(matches)} 个匹配'
                        )
                    
                    if scanned_count % 100 == 0:
                        logger.info(f"已扫描 {scanned_count}/{total_stocks} 只股票，找到 {len(matches)} 个匹配")
                
                except Exception as e:
                    logger.error(f"扫描股票失败 {stock_code}: {e}")
                    continue
            
            logger.info(f"扫描完成: 共扫描 {scanned_count} 只股票，找到 {len(matches)} 个匹配")
            
            # 保存执行结果
            if progress_callback:
                progress_callback(90, '正在保存结果...')
            
            saved_count = self._save_results(strategy_id, matches)
            logger.info(f"保存执行结果: {saved_count} 条")
            
            # 更新策略的最后执行时间
            self.strategy_service.update_last_execution(strategy_id)
            
            # 计算执行时间
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            if progress_callback:
                progress_callback(100, '执行完成')
            
            return {
                'success': True,
                'strategy_id': strategy_id,
                'strategy_name': strategy['name'],
                'scanned_stocks': scanned_count,
                'matched_count': len(matches),
                'saved_count': saved_count,
                'execution_time': execution_time,
                'matches': matches[:100]  # 只返回前100个匹配，避免数据量过大
            }
            
        except Exception as e:
            logger.error(f"执行策略失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_stocks_with_data(self, limit: Optional[int] = None) -> List[Dict[str, str]]:
        """
        获取有行情数据的股票列表
        
        Args:
            limit: 限制返回的股票数量
            
        Returns:
            股票列表
        """
        try:
            # 从DuckDB中获取有数据的股票代码
            sql = """
                SELECT DISTINCT code as stock_code
                FROM daily_market
                ORDER BY code
            """
            
            if limit:
                sql += f" LIMIT {limit}"
            
            result = self.duckdb.execute_query(sql)
            
            if not result:
                return []
            
            stock_codes = [row['stock_code'] for row in result]
            
            # 从SQLite中获取股票详细信息
            placeholders = ','.join(['?' for _ in stock_codes])
            sql = f"""
                SELECT code as stock_code, name as stock_name, market_type as market
                FROM stocks
                WHERE code IN ({placeholders})
                ORDER BY code
            """
            
            stocks = self.db.execute_query(sql, tuple(stock_codes))
            
            return stocks
            
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            return []
    
    def _scan_stock(self, stock_code: str, stock_name: str,
                   start_date: str, end_date: str,
                   rise_threshold: float, observation_days: int, 
                   ma_period: int) -> List[Dict[str, Any]]:
        """
        扫描单只股票，查找符合条件的交易日
        
        Args:
            stock_code: 股票代码
            stock_name: 股票名称
            start_date: 开始日期
            end_date: 结束日期
            rise_threshold: 涨幅阈值
            observation_days: 观察天数
            ma_period: 均线周期
            
        Returns:
            匹配的交易日列表
        """
        matches = []
        
        try:
            # 获取股票的历史行情数据
            # 需要额外获取更多天数的数据，用于计算均线和后续观察
            buffer_days = max(ma_period, observation_days) + 60  # 额外60天用于计算均线
            
            extended_start = (datetime.strptime(start_date, '%Y-%m-%d') - 
                            timedelta(days=buffer_days)).strftime('%Y-%m-%d')
            
            sql = """
                SELECT trade_date, open, high, low, close, volume, amount, change_pct as pct_change
                FROM daily_market
                WHERE code = ?
                  AND trade_date >= ?
                  AND trade_date <= ?
                ORDER BY trade_date
            """
            
            data = self.duckdb.execute_query(sql, (stock_code, extended_start, end_date))
            
            if not data or len(data) < ma_period + observation_days:
                return []
            
            # 将list转换为pandas DataFrame
            import pandas as pd
            df = pd.DataFrame(data)
            
            # 确保trade_date是字符串格式，避免类型比较错误
            if len(df) > 0 and not isinstance(df['trade_date'].iloc[0], str):
                df['trade_date'] = df['trade_date'].astype(str)
            
            # 计算移动平均线
            data_with_ma = self.indicators.calculate_ma(df, ma_period)
            
            # 过滤日期范围
            mask = (data_with_ma['trade_date'] >= start_date) & (data_with_ma['trade_date'] <= end_date)
            data_in_range = data_with_ma[mask]
            
            # 查找大涨日
            big_rise_df = self.indicators.find_big_rise_days(
                data_in_range, 
                rise_threshold
            )
            
            if big_rise_df.empty:
                return []
            
            # 将DataFrame转换为list of dict
            big_rise_days = big_rise_df.to_dict('records')
            
            if not big_rise_days:
                return []
            
            # 检查每个大涨日后续是否满足条件
            for rise_day in big_rise_days:
                rise_date = rise_day['trade_date']
                rise_pct = rise_day['pct_change']
                
                # 检查后续N天是否都站在均线之上
                is_valid, observation_result = self._check_observation_period(
                    data_with_ma,
                    rise_date,
                    observation_days,
                    ma_period
                )
                
                if is_valid:
                    matches.append({
                        'stock_code': stock_code,
                        'stock_name': stock_name,
                        'trigger_date': rise_date,
                        'trigger_pct_change': rise_pct,
                        'observation_days': observation_days,
                        'ma_period': ma_period,
                        'observation_result': observation_result
                    })
            
            return matches
            
        except Exception as e:
            logger.error(f"扫描股票失败 {stock_code}: {e}")
            return []
    
    def _check_observation_period(self, data: 'pd.DataFrame', 
                                 trigger_date: str,
                                 observation_days: int,
                                 ma_period: int) -> Tuple[bool, Dict[str, Any]]:
        """
        检查观察期内是否满足条件
        
        Args:
            data: 行情数据（DataFrame，包含均线）
            trigger_date: 触发日期
            observation_days: 观察天数
            ma_period: 均线周期
            
        Returns:
            (是否满足条件, 观察结果详情)
        """
        try:
            # 将DataFrame转换为list以便索引访问
            data_list = data.to_dict('records')
            
            # 找到触发日期的索引
            trigger_idx = None
            for i, row in enumerate(data_list):
                if row['trade_date'] == trigger_date:
                    trigger_idx = i
                    break
            
            if trigger_idx is None:
                return False, {}
            
            # 检查后续N天的数据
            ma_key = f'ma_{ma_period}'
            observation_result = {
                'days_checked': 0,
                'days_above_ma': 0,
                'details': []
            }
            
            for i in range(1, observation_days + 1):
                next_idx = trigger_idx + i
                
                if next_idx >= len(data_list):
                    # 数据不足，无法完成观察
                    return False, observation_result
                
                next_day = data_list[next_idx]
                close_price = next_day['close']
                ma_value = next_day.get(ma_key)
                
                if ma_value is None or pd.isna(ma_value):
                    # 均线数据不足
                    return False, observation_result
                
                observation_result['days_checked'] += 1
                
                is_above_ma = close_price > ma_value
                
                if is_above_ma:
                    observation_result['days_above_ma'] += 1
                
                observation_result['details'].append({
                    'date': next_day['trade_date'],
                    'close': close_price,
                    f'ma{ma_period}': ma_value,
                    'above_ma': is_above_ma
                })
                
                # 如果有任何一天不满足条件，直接返回False
                if not is_above_ma:
                    return False, observation_result
            
            # 所有天数都满足条件
            return True, observation_result
            
        except Exception as e:
            logger.error(f"检查观察期失败: {e}")
            return False, {}
    
    def _save_results(self, strategy_id: int, matches: List[Dict[str, Any]]) -> int:
        """
        保存策略执行结果
        
        Args:
            strategy_id: 策略ID
            matches: 匹配结果列表
            
        Returns:
            保存的记录数
        """
        try:
            if not matches:
                return 0
            
            # 删除该策略的旧结果
            self.db.execute_update(
                "DELETE FROM strategy_results WHERE strategy_id = ?",
                (strategy_id,)
            )
            
            # 插入新结果
            sql = """
                INSERT INTO strategy_results 
                (strategy_id, stock_code, stock_name, trigger_date, 
                 trigger_pct_change, observation_days, ma_period, 
                 observation_result, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            saved_count = 0
            
            for match in matches:
                import json
                from decimal import Decimal
                
                # 转换Decimal为float以便JSON序列化
                def convert_decimal(obj):
                    if isinstance(obj, Decimal):
                        return float(obj)
                    elif isinstance(obj, dict):
                        return {k: convert_decimal(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [convert_decimal(v) for v in obj]
                    return obj
                
                observation_result = convert_decimal(match['observation_result'])
                
                self.db.execute_update(
                    sql,
                    (
                        strategy_id,
                        match['stock_code'],
                        match['stock_name'],
                        match['trigger_date'],
                        float(match['trigger_pct_change']),
                        int(match['observation_days']),
                        int(match['ma_period']),
                        json.dumps(observation_result, ensure_ascii=False),
                        now
                    )
                )
                saved_count += 1
            
            return saved_count
            
        except Exception as e:
            logger.error(f"保存执行结果失败: {e}")
            import traceback
            traceback.print_exc()
            return 0
    
    def get_strategy_results(self, strategy_id: int, 
                           limit: int = 100,
                           offset: int = 0) -> List[Dict[str, Any]]:
        """
        获取策略执行结果
        
        Args:
            strategy_id: 策略ID
            limit: 返回记录数
            offset: 偏移量
            
        Returns:
            执行结果列表
        """
        try:
            sql = """
                SELECT *
                FROM strategy_results
                WHERE strategy_id = ?
                ORDER BY trigger_date DESC, stock_code
                LIMIT ? OFFSET ?
            """
            
            results = self.db.execute_query(
                sql,
                (strategy_id, limit, offset)
            )
            
            # 解析observation_result JSON
            import json
            for result in results:
                result['observation_result'] = json.loads(result['observation_result'])
            
            return results
            
        except Exception as e:
            logger.error(f"获取策略结果失败: {e}")
            return []
    
    def get_strategy_results_count(self, strategy_id: int) -> int:
        """
        获取策略执行结果数量
        
        Args:
            strategy_id: 策略ID
            
        Returns:
            结果数量
        """
        try:
            result = self.db.execute_query(
                "SELECT COUNT(*) as count FROM strategy_results WHERE strategy_id = ?",
                (strategy_id,)
            )
            
            if result:
                return result[0]['count']
            
            return 0
            
        except Exception as e:
            logger.error(f"获取策略结果数量失败: {e}")
            return 0
    
    def clear_strategy_results(self, strategy_id: int) -> bool:
        """
        清空策略执行结果
        
        Args:
            strategy_id: 策略ID
            
        Returns:
            是否成功
        """
        try:
            self.db.execute_update(
                "DELETE FROM strategy_results WHERE strategy_id = ?",
                (strategy_id,)
            )
            
            logger.info(f"清空策略结果成功: strategy_id={strategy_id}")
            return True
            
        except Exception as e:
            logger.error(f"清空策略结果失败: {e}")
            return False


# 全局策略执行器实例
_strategy_executor = None


def get_strategy_executor() -> StrategyExecutor:
    """获取策略执行器实例（单例模式）"""
    global _strategy_executor
    if _strategy_executor is None:
        _strategy_executor = StrategyExecutor()
    return _strategy_executor
