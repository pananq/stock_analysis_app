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
                WHERE code = ?
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
            
            if new_earliest is not None:
                updates.append("earliest_data_date = ?")
                params.append(new_earliest.strftime('%Y-%m-%d'))
            
            if new_latest is not None:
                updates.append("latest_data_date = ?")
                params.append(new_latest.strftime('%Y-%m-%d'))
            
            if not updates:
                # 没有需要更新的字段
                return True
            
            updates.append("updated_at = ?")
            params.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            params.append(stock_code)
            
            query = f"UPDATE stocks SET {', '.join(updates)} WHERE code = ?"
            affected_rows = self.db.execute_update(query, tuple(params))
            
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
