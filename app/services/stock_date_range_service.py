"""
股票数据时间范围管理服务
负责管理股票的历史数据日期范围，支持增量更新判断
"""

from datetime import datetime, date
from typing import Optional, Tuple, Dict, Any
from app.utils import get_logger
from app.utils.trading_day import has_trading_days_between, is_trading_day


class StockDateRangeService:
    """股票数据时间范围服务类"""
    
    def __init__(self, database):
        """
        初始化服务
        
        Args:
            database: 数据库实例
        """
        self.db = database
        self.logger = get_logger(__name__)
    
    def get_stock_date_range(self, stock_code: str) -> Tuple[Optional[date], Optional[date]]:
        """
        获取股票的数据时间范围
        
        Args:
            stock_code: 股票代码
            
        Returns:
            Tuple[earliest_date, latest_date]: (最早日期, 最近日期)，如果没有数据则返回 (None, None)
        """
        try:
            query = '''
                SELECT earliest_data_date, latest_data_date
                FROM stocks
                WHERE code = %s
            '''
            results = self.db.execute_query(query, (stock_code,))
            
            if results and len(results) > 0:
                row = results[0]
                earliest = row.get('earliest_data_date')
                latest = row.get('latest_data_date')
                
                # 将字符串转换为date对象
                if earliest and isinstance(earliest, str):
                    earliest = datetime.strptime(earliest, '%Y-%m-%d').date()
                if latest and isinstance(latest, str):
                    latest = datetime.strptime(latest, '%Y-%m-%d').date()
                
                return (earliest, latest)
            
            return (None, None)
        except Exception as e:
            self.logger.error(f"获取股票{stock_code}的日期范围失败: {e}", exc_info=True)
            return (None, None)
    
    def update_stock_date_range(
        self,
        stock_code: str,
        earliest_date: Optional[date] = None,
        latest_date: Optional[date] = None
    ) -> bool:
        """
        更新股票的数据时间范围
        
        Args:
            stock_code: 股票代码
            earliest_date: 最早日期，如果为None则不更新该字段
            latest_date: 最近日期，如果为None则不更新该字段
            
        Returns:
            bool: 更新是否成功
        """
        try:
            # 获取当前的时间范围
            current_earliest, current_latest = self.get_stock_date_range(stock_code)
            
            # 确定新的日期范围
            new_earliest = earliest_date
            new_latest = latest_date
            
            # 如果earliest_date为None，保持原值；如果原值为None，使用新值；否则取最小值
            if new_earliest is None:
                new_earliest = current_earliest
            elif current_earliest is not None:
                new_earliest = min(new_earliest, current_earliest)
            
            # 如果latest_date为None，保持原值；如果原值为None，使用新值；否则取最大值
            if new_latest is None:
                new_latest = current_latest
            elif current_latest is not None:
                new_latest = max(new_latest, current_latest)
            
            # 构建更新语句
            updates = []
            params = []
            
            self.logger.debug(f"股票{stock_code}日期范围计算结果: new_earliest={new_earliest} (type: {type(new_earliest)}), new_latest={new_latest} (type: {type(new_latest)})")
            
            if new_earliest is not None:
                updates.append("earliest_data_date = %s")
                earliest_str = new_earliest.strftime('%Y-%m-%d') if isinstance(new_earliest, (date, datetime)) else str(new_earliest)
                params.append(earliest_str)
                self.logger.debug(f"添加earliest_data_date更新: {earliest_str}")
            
            if new_latest is not None:
                updates.append("latest_data_date = %s")
                latest_str = new_latest.strftime('%Y-%m-%d') if isinstance(new_latest, (date, datetime)) else str(new_latest)
                params.append(latest_str)
                self.logger.debug(f"添加latest_data_date更新: {latest_str}")
            
            if not updates:
                # 没有需要更新的字段
                self.logger.debug(f"股票{stock_code}没有需要更新的字段，跳过")
                return True
            
            updates.append("updated_at = %s")
            params.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            params.append(stock_code)
            
            query = f"UPDATE stocks SET {', '.join(updates)} WHERE code = %s"
            self.logger.debug(f"执行SQL更新: {query}")
            self.logger.debug(f"SQL参数: {params}")
            
            affected_rows = self.db.execute_update(query, tuple(params))
            self.logger.debug(f"SQL执行完成，影响行数: {affected_rows}")
            
            if affected_rows > 0:
                self.logger.debug(f"更新股票{stock_code}的日期范围: earliest={new_earliest}, latest={new_latest}")
                return True
            else:
                self.logger.warning(f"更新股票{stock_code}的日期范围失败: 未找到股票")
                return False
            
        except Exception as e:
            self.logger.error(f"更新股票{stock_code}的日期范围失败: {e}", exc_info=True)
            return False
    
    def needs_update(self, stock_code: str, current_date: date = None) -> Tuple[bool, str]:
        """
        判断股票是否需要更新数据
        
        Args:
            stock_code: 股票代码
            current_date: 当前日期，如果为None则使用今天
            
        Returns:
            Tuple[needs_update, reason]: (是否需要更新, 原因)
        """
        if current_date is None:
            current_date = date.today()
        
        # 获取当前的时间范围
        earliest, latest = self.get_stock_date_range(stock_code)
        
        # 如果没有数据，需要更新
        if latest is None:
            return (True, "首次下载数据")
        
        # 如果最新日期已经是今天，不需要更新
        if latest == current_date:
            return (False, "数据已是最新")
        
        # 判断最新日期到当前日期之间是否有交易日
        next_day = latest + datetime.timedelta(days=1)
        has_trading = has_trading_days_between(next_day, current_date)
        
        if not has_trading:
            return (False, "期间无交易日")
        
        return (True, f"需要从{next_day}开始更新")
    
    def calculate_update_start_date(self, stock_code: str, current_date: date = None) -> Optional[date]:
        """
        计算增量更新的起始日期
        
        Args:
            stock_code: 股票代码
            current_date: 当前日期，如果为None则使用今天
            
        Returns:
            Optional[date]: 起始日期，如果不需要更新则返回None
        """
        if current_date is None:
            current_date = date.today()
        
        # 获取当前的时间范围
        _, latest = self.get_stock_date_range(stock_code)
        
        # 如果没有数据，从当前日期开始
        if latest is None:
            return current_date
        
        # 如果最新日期已经是今天，不需要更新
        if latest == current_date:
            return None
        
        # 从最新日期的下一天开始更新
        return latest + datetime.timedelta(days=1)
    
    def get_stocks_needing_update(self, current_date: date = None) -> list:
        """
        获取需要更新的股票列表
        
        Args:
            current_date: 当前日期，如果为None则使用今天
            
        Returns:
            list: 需要更新的股票代码列表
        """
        if current_date is None:
            current_date = date.today()
        
        # 获取所有股票
        query = "SELECT code, name, latest_data_date FROM stocks WHERE status = 'normal' ORDER BY code"
        results = self.db.execute_query(query)
        
        stocks_needing_update = []
        
        for row in results:
            stock_code = row['code']
            stock_name = row['name']
            latest = row.get('latest_data_date')
            
            # 转换为date对象
            if latest and isinstance(latest, str):
                latest = datetime.strptime(latest, '%Y-%m-%d').date()
            
            # 判断是否需要更新
            needs, reason = self.needs_update(stock_code, current_date)
            
            if needs:
                stocks_needing_update.append({
                    'code': stock_code,
                    'name': stock_name,
                    'latest_date': latest,
                    'reason': reason
                })
        
        return stocks_needing_update
    
    def get_stock_date_range_dict(self, stock_code: str) -> Dict[str, Any]:
        """
        获取股票的数据时间范围（字典格式）
        
        Args:
            stock_code: 股票代码
            
        Returns:
            Dict: 包含时间范围信息的字典
        """
        earliest, latest = self.get_stock_date_range(stock_code)
        
        result = {
            'code': stock_code,
            'earliest_data_date': earliest.strftime('%Y-%m-%d') if earliest else None,
            'latest_data_date': latest.strftime('%Y-%m-%d') if latest else None,
            'has_data': earliest is not None and latest is not None
        }
        
        # 计算天数统计
        if earliest and latest:
            days = (latest - earliest).days + 1
            result['data_days'] = days
        
        return result
    
    def update_date_range_from_data(self, stock_code: str, data_list: list) -> Tuple[bool, int]:
        """
        根据数据列表更新股票的时间范围
        
        Args:
            stock_code: 股票代码
            data_list: 数据列表，每个元素应包含trade_date字段
            
        Returns:
            Tuple[success, count]: (是否成功, 数据条数)
        """
        if not data_list:
            return (True, 0)
        
        try:
            # 提取所有交易日期
            dates = []
            for item in data_list:
                trade_date = item.get('trade_date')
                if trade_date:
                    if isinstance(trade_date, str):
                        trade_date = datetime.strptime(trade_date, '%Y-%m-%d').date()
                    elif isinstance(trade_date, datetime):
                        trade_date = trade_date.date()
                    dates.append(trade_date)
            
            if not dates:
                return (True, 0)
            
            # 计算最小和最大日期
            earliest_date = min(dates)
            latest_date = max(dates)
            
            # 更新时间范围
            success = self.update_stock_date_range(
                stock_code,
                earliest_date=earliest_date,
                latest_date=latest_date
            )
            
            return (success, len(data_list))
        
        except Exception as e:
            self.logger.error(f"根据数据更新股票{stock_code}的日期范围失败: {e}", exc_info=True)
            return (False, 0)
    
    def get_stock_date_range_from_daily_market(self, stock_code: str) -> Tuple[Optional[date], Optional[date]]:
        """
        从 daily_market 表中查询股票的最小和最大交易日期
        
        Args:
            stock_code: 股票代码
            
        Returns:
            Tuple[earliest_date, latest_date]: (最早日期, 最近日期)，如果没有数据则返回 (None, None)
        """
        try:
            query = '''
                SELECT MIN(trade_date) as min_date, MAX(trade_date) as max_date
                FROM daily_market
                WHERE code = %s
            '''
            results = self.db.execute_query(query, (stock_code,))
            
            if results and len(results) > 0:
                row = results[0]
                min_date = row.get('min_date')
                max_date = row.get('max_date')
                
                # 将字符串转换为date对象
                if min_date and isinstance(min_date, str):
                    min_date = datetime.strptime(min_date, '%Y-%m-%d').date()
                if max_date and isinstance(max_date, str):
                    max_date = datetime.strptime(max_date, '%Y-%m-%d').date()
                
                return (min_date, max_date)
            
            return (None, None)
        except Exception as e:
            self.logger.error(f"从 daily_market 查询股票{stock_code}的日期范围失败: {e}", exc_info=True)
            return (None, None)
    
    def batch_get_stock_date_range_from_daily_market(self, stock_codes: list) -> Dict[str, Tuple[Optional[date], Optional[date]]]:
        """
        批量查询多只股票在 daily_market 表中的日期范围
        
        Args:
            stock_codes: 股票代码列表
            
        Returns:
            Dict[stock_code, Tuple[earliest_date, latest_date]]: 股票代码到日期范围的映射
        """
        if not stock_codes:
            return {}
        
        try:
            # 使用 IN 子句批量查询
            placeholders = ','.join(['%s'] * len(stock_codes))
            query = f'''
                SELECT code, MIN(trade_date) as min_date, MAX(trade_date) as max_date
                FROM daily_market
                WHERE code IN ({placeholders})
                GROUP BY code
            '''
            
            results = self.db.execute_query(query, tuple(stock_codes))
            
            result_dict = {}
            for row in results:
                stock_code = row['code']
                min_date = row.get('min_date')
                max_date = row.get('max_date')
                
                # 将字符串转换为date对象
                if min_date and isinstance(min_date, str):
                    min_date = datetime.strptime(min_date, '%Y-%m-%d').date()
                if max_date and isinstance(max_date, str):
                    max_date = datetime.strptime(max_date, '%Y-%m-%d').date()
                
                result_dict[stock_code] = (min_date, max_date)
            
            # 对于没有数据的股票，返回 (None, None)
            for stock_code in stock_codes:
                if stock_code not in result_dict:
                    result_dict[stock_code] = (None, None)
            
            return result_dict
        
        except Exception as e:
            self.logger.error(f"批量查询 daily_market 日期范围失败: {e}", exc_info=True)
            # 返回空结果，表示查询失败
            return {code: (None, None) for code in stock_codes}
    
    def batch_update_stock_date_ranges(self, updates: Dict[str, Tuple[Optional[date], Optional[date]]]) -> int:
        """
        批量更新多只股票的日期字段
        
        Args:
            updates: 字典，格式为 {stock_code: (earliest_date, latest_date)}
                    如果 earliest_date 或 latest_date 为 None，则不更新该字段
            
        Returns:
            int: 成功更新的股票数量
        """
        if not updates:
            return 0
        
        success_count = 0
        
        try:
            for stock_code, (earliest_date, latest_date) in updates.items():
                if self.update_stock_date_range(stock_code, earliest_date, latest_date):
                    success_count += 1
            
            return success_count
        
        except Exception as e:
            self.logger.error(f"批量更新股票日期字段失败: {e}", exc_info=True)
            return success_count
    
    def batch_update_stock_date_ranges_optimized(self, updates: Dict[str, Tuple[Optional[date], Optional[date]]], batch_size: int = 100) -> int:
        """
        批量更新多只股票的日期字段（优化版，使用批量 SQL）
        
        Args:
            updates: 字典，格式为 {stock_code: (earliest_date, latest_date)}
                    如果 earliest_date 或 latest_date 为 None，则不更新该字段
            batch_size: 每批更新的股票数量，默认为 100
            
        Returns:
            int: 成功更新的股票数量
        """
        if not updates:
            return 0
        
        success_count = 0
        total = len(updates)
        
        try:
            # 将字典转换为列表，便于分批处理
            update_list = list(updates.items())
            
            # 分批处理
            for i in range(0, total, batch_size):
                batch = update_list[i:i + batch_size]
                batch_dict = dict(batch)
                
                # 执行批量更新
                if self._execute_batch_update(batch_dict):
                    success_count += len(batch)
                    self.logger.info(f"批量更新日期字段进度: {success_count}/{total}")
            
            self.logger.info(f"批量更新股票日期字段完成，成功: {success_count}/{total}")
            return success_count
        
        except Exception as e:
            self.logger.error(f"批量更新股票日期字段失败: {e}", exc_info=True)
            return success_count
    
    def _execute_batch_update(self, updates: Dict[str, Tuple[Optional[date], Optional[date]]]) -> bool:
        """
        执行批量更新的内部方法
        
        Args:
            updates: 字典，格式为 {stock_code: (earliest_date, latest_date)}
            
        Returns:
            bool: 是否全部成功
        """
        if not updates:
            return True
        
        try:
            # 构建批量更新 SQL
            # 使用 CASE WHEN 语句实现单条 SQL 更新多条记录
            cases_earliest = []
            cases_latest = []
            stock_codes = []
            params = []
            
            for stock_code, (earliest_date, latest_date) in updates.items():
                stock_codes.append(stock_code)
                
                if earliest_date is not None:
                    earliest_str = earliest_date.strftime('%Y-%m-%d') if isinstance(earliest_date, (date, datetime)) else str(earliest_date)
                    cases_earliest.append(f"WHEN %s THEN %s")
                    params.extend([stock_code, earliest_str])
                
                if latest_date is not None:
                    latest_str = latest_date.strftime('%Y-%m-%d') if isinstance(latest_date, (date, datetime)) else str(latest_date)
                    cases_latest.append(f"WHEN %s THEN %s")
                    params.extend([stock_code, latest_str])
            
            # 如果没有需要更新的字段，直接返回成功
            if not cases_earliest and not cases_latest:
                return True
            
            # 构建 SQL 语句
            set_clauses = []
            
            if cases_earliest:
                # 添加 ELSE 子句，保持原有值不变
                set_clauses.append(f"earliest_data_date = CASE code {' '.join(cases_earliest)} ELSE earliest_data_date END")
            
            if cases_latest:
                # 添加 ELSE 子句，保持原有值不变
                set_clauses.append(f"latest_data_date = CASE code {' '.join(cases_latest)} ELSE latest_data_date END")
            
            # 添加 updated_at 字段更新
            set_clauses.append(f"updated_at = %s")
            params.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            
            # 添加 WHERE 子句参数
            placeholders = ','.join(['%s'] * len(stock_codes))
            params.extend(stock_codes)
            
            query = f"""
                UPDATE stocks
                SET {', '.join(set_clauses)}
                WHERE code IN ({placeholders})
            """
            
            self.logger.debug(f"执行批量更新 SQL，影响股票数: {len(stock_codes)}")
            affected_rows = self.db.execute_update(query, tuple(params))
            
            if affected_rows > 0:
                self.logger.debug(f"批量更新成功，影响行数: {affected_rows}")
                return True
            else:
                self.logger.warning(f"批量更新未影响任何行")
                return False
        
        except Exception as e:
            self.logger.error(f"执行批量更新失败: {e}", exc_info=True)
            return False
    
    def get_stocks_with_null_date_range(self) -> list:
        """
        获取日期字段为 NULL 的股票列表
        
        Returns:
            list: 股票代码列表
        """
        try:
            query = """
                SELECT code, name, earliest_data_date, latest_data_date
                FROM stocks
                WHERE earliest_data_date IS NULL AND latest_data_date IS NULL
                ORDER BY code
            """
            results = self.db.execute_query(query)
            
            return [
                {
                    'code': row['code'],
                    'name': row['name'],
                    'earliest_data_date': row.get('earliest_data_date'),
                    'latest_data_date': row.get('latest_data_date')
                }
                for row in results
            ]
        
        except Exception as e:
            self.logger.error(f"查询日期字段为 NULL 的股票失败: {e}", exc_info=True)
            return []
