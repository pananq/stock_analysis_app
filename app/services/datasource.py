"""
数据源抽象接口
定义统一的数据源接口，支持akshare和tushare
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import pandas as pd


class DataSource(ABC):
    """数据源抽象基类"""
    
    @abstractmethod
    def get_stock_list(self) -> pd.DataFrame:
        """
        获取股票列表
        
        Returns:
            包含股票信息的DataFrame，至少包含以下列：
            - code: 股票代码
            - name: 股票名称
            - list_date: 上市日期
            - industry: 所属行业
            - market_type: 市场类型（主板/创业板/科创板等）
        """
        pass
    
    @abstractmethod
    def get_stock_daily(self, stock_code: str, start_date: str = None, 
                       end_date: str = None) -> pd.DataFrame:
        """
        获取股票日线行情数据
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期（YYYY-MM-DD）
            end_date: 结束日期（YYYY-MM-DD）
            
        Returns:
            包含行情数据的DataFrame，至少包含以下列：
            - trade_date: 交易日期
            - open: 开盘价
            - close: 收盘价
            - high: 最高价
            - low: 最低价
            - volume: 成交量
            - amount: 成交额
            - change_percent: 涨跌幅（百分比）
        """
        pass
    
    @abstractmethod
    def get_trading_dates(self, start_date: str = None, 
                         end_date: str = None) -> List[str]:
        """
        获取交易日历
        
        Args:
            start_date: 开始日期（YYYY-MM-DD）
            end_date: 结束日期（YYYY-MM-DD）
            
        Returns:
            交易日期列表
        """
        pass
    
    @abstractmethod
    def is_trading_day(self, date: str) -> bool:
        """
        判断是否为交易日
        
        Args:
            date: 日期（YYYY-MM-DD）
            
        Returns:
            是否为交易日
        """
        pass
    
    def normalize_stock_code(self, code: str) -> str:
        """
        标准化股票代码
        
        Args:
            code: 原始股票代码
            
        Returns:
            标准化后的股票代码
        """
        # 移除可能的前缀和后缀
        code = code.strip().upper()
        # 只保留数字部分
        if '.' in code:
            code = code.split('.')[0]
        return code
