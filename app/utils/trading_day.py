"""
交易日判断工具
用于判断两个日期之间是否存在交易日
"""

from datetime import datetime, date, timedelta
from typing import List, Set
import calendar


class TradingDayHelper:
    """交易日助手类"""
    
    # A股市场法定节假日（可配置）
    # 注意：这里只包含固定的节假日，动态的节假日（如春节）需要外部配置
    DEFAULT_HOLIDAYS = [
        # 元旦（1月1日）
        '01-01',
        # 清明节（4月4日或5日，根据当年调整）
        # '04-04',  # 暂不包含，需要根据年份动态调整
        # '04-05',
        # 劳动节（5月1日-5月3日）
        '05-01', '05-02', '05-03',
        # 端午节（农历五月初五，需要根据年份动态调整）
        # 暂不包含，需要农历计算
        # 中秋节（农历八月十五，需要根据年份动态调整）
        # 暂不包含，需要农历计算
        # 国庆节（10月1日-10月7日）
        '10-01', '10-02', '10-03', '10-04', '10-05', '10-06', '10-07',
    ]
    
    def __init__(self, holidays: List[str] = None, use_simplified: bool = True):
        """
        初始化交易日助手
        
        Args:
            holidays: 自定义节假日列表，格式为 'MM-DD'
            use_simplified: 是否使用简化模式（只排除周末，不排除法定节假日）
        """
        self.use_simplified = use_simplified
        
        if holidays is None:
            self.holidays = set()
        else:
            self.holidays = set(holidays)
        
        # 添加默认节假日
        if not self.use_simplified and holidays is None:
            self.holidays = set(self.DEFAULT_HOLIDAYS)
    
    def is_weekend(self, date_obj: date) -> bool:
        """
        判断是否为周末
        
        Args:
            date_obj: 日期对象
            
        Returns:
            bool: True表示是周末
        """
        return date_obj.weekday() >= 5  # 5=周六, 6=周日
    
    def is_holiday(self, date_obj: date) -> bool:
        """
        判断是否为法定节假日
        
        Args:
            date_obj: 日期对象
            
        Returns:
            bool: True表示是节假日
        """
        if self.use_simplified:
            return False
        
        holiday_str = date_obj.strftime('%m-%d')
        return holiday_str in self.holidays
    
    def is_trading_day(self, date_obj: date) -> bool:
        """
        判断是否为交易日
        
        Args:
            date_obj: 日期对象
            
        Returns:
            bool: True表示是交易日
        """
        return not self.is_weekend(date_obj) and not self.is_holiday(date_obj)
    
    def has_trading_days_between(self, start_date: date, end_date: date) -> bool:
        """
        判断两个日期之间是否存在交易日
        
        Args:
            start_date: 开始日期（包含）
            end_date: 结束日期（包含）
            
        Returns:
            bool: True表示存在交易日
        """
        if start_date > end_date:
            return False
        
        if start_date == end_date:
            return self.is_trading_day(start_date)
        
        current_date = start_date
        while current_date <= end_date:
            if self.is_trading_day(current_date):
                return True
            current_date += timedelta(days=1)
        
        return False
    
    def get_trading_days_between(self, start_date: date, end_date: date) -> List[date]:
        """
        获取两个日期之间的所有交易日
        
        Args:
            start_date: 开始日期（包含）
            end_date: 结束日期（包含）
            
        Returns:
            List[date]: 交易日列表
        """
        trading_days = []
        current_date = start_date
        while current_date <= end_date:
            if self.is_trading_day(current_date):
                trading_days.append(current_date)
            current_date += timedelta(days=1)
        return trading_days
    
    def count_trading_days_between(self, start_date: date, end_date: date) -> int:
        """
        计算两个日期之间的交易日数量
        
        Args:
            start_date: 开始日期（包含）
            end_date: 结束日期（包含）
            
        Returns:
            int: 交易日数量
        """
        count = 0
        current_date = start_date
        while current_date <= end_date:
            if self.is_trading_day(current_date):
                count += 1
            current_date += timedelta(days=1)
        return count
    
    def add_holidays(self, holidays: List[str]):
        """
        添加节假日
        
        Args:
            holidays: 节假日列表，格式为 'MM-DD'
        """
        self.holidays.update(holidays)
    
    def remove_holidays(self, holidays: List[str]):
        """
        移除节假日
        
        Args:
            holidays: 节假日列表，格式为 'MM-DD'
        """
        for holiday in holidays:
            self.holidays.discard(holiday)
    
    def get_next_trading_day(self, date_obj: date, max_days: int = 7) -> date:
        """
        获取指定日期后的下一个交易日
        
        Args:
            date_obj: 日期对象
            max_days: 最大查找天数
            
        Returns:
            date: 下一个交易日
        """
        current_date = date_obj + timedelta(days=1)
        count = 0
        while count < max_days:
            if self.is_trading_day(current_date):
                return current_date
            current_date += timedelta(days=1)
            count += 1
        return None
    
    def get_previous_trading_day(self, date_obj: date, max_days: int = 7) -> date:
        """
        获取指定日期前的上一个交易日
        
        Args:
            date_obj: 日期对象
            max_days: 最大查找天数
            
        Returns:
            date: 上一个交易日
        """
        current_date = date_obj - timedelta(days=1)
        count = 0
        while count < max_days:
            if self.is_trading_day(current_date):
                return current_date
            current_date -= timedelta(days=1)
            count += 1
        return None


# 创建默认的交易日助手实例（使用简化模式）
default_helper = TradingDayHelper(use_simplified=True)


def is_trading_day(date_obj: date) -> bool:
    """
    判断是否为交易日（使用默认助手）
    
    Args:
        date_obj: 日期对象
        
    Returns:
        bool: True表示是交易日
    """
    return default_helper.is_trading_day(date_obj)


def has_trading_days_between(start_date: date, end_date: date) -> bool:
    """
    判断两个日期之间是否存在交易日（使用默认助手）
    
    Args:
        start_date: 开始日期（包含）
        end_date: 结束日期（包含）
        
    Returns:
        bool: True表示存在交易日
    """
    return default_helper.has_trading_days_between(start_date, end_date)
