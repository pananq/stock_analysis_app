"""
技术指标计算类

提供常用的技术指标计算功能，包括：
- 移动平均线（MA）
- 涨跌幅
- 成交量分析
- 其他技术指标
"""

import pandas as pd
import numpy as np
from typing import Union, List, Optional
from app.utils import get_logger

logger = get_logger(__name__)


class TechnicalIndicators:
    """技术指标计算类"""
    
    @staticmethod
    def calculate_ma(data: pd.DataFrame, periods: Union[int, List[int]] = None, 
                     price_column: str = 'close') -> pd.DataFrame:
        """
        计算移动平均线（Moving Average）
        
        Args:
            data: 包含价格数据的DataFrame，必须包含指定的价格列
            periods: 均线周期，可以是单个整数或整数列表，默认为[5, 10, 20, 30, 60]
            price_column: 用于计算均线的价格列名，默认为'close'
            
        Returns:
            添加了均线列的DataFrame，列名格式为'ma_5', 'ma_10'等
        """
        if data.empty:
            logger.warning("输入数据为空，无法计算均线")
            return data
        
        if price_column not in data.columns:
            logger.error(f"数据中不存在列: {price_column}")
            return data
        
        # 默认计算5、10、20、30、60日均线
        if periods is None:
            periods = [5, 10, 20, 30, 60]
        elif isinstance(periods, int):
            periods = [periods]
        
        result = data.copy()
        
        for period in periods:
            col_name = f'ma_{period}'
            result[col_name] = result[price_column].rolling(window=period, min_periods=1).mean()
            logger.debug(f"计算 {period} 日均线完成")
        
        return result
    
    @staticmethod
    def calculate_change_pct(data: pd.DataFrame, price_column: str = 'close') -> pd.DataFrame:
        """
        计算涨跌幅（百分比）
        
        Args:
            data: 包含价格数据的DataFrame
            price_column: 用于计算涨跌幅的价格列名，默认为'close'
            
        Returns:
            添加了涨跌幅列的DataFrame，列名为'change_pct'
        """
        if data.empty:
            logger.warning("输入数据为空，无法计算涨跌幅")
            return data
        
        if price_column not in data.columns:
            logger.error(f"数据中不存在列: {price_column}")
            return data
        
        result = data.copy()
        result['change_pct'] = result[price_column].pct_change() * 100
        
        logger.debug("计算涨跌幅完成")
        return result
    
    @staticmethod
    def calculate_change_amount(data: pd.DataFrame, price_column: str = 'close') -> pd.DataFrame:
        """
        计算涨跌额（绝对值）
        
        Args:
            data: 包含价格数据的DataFrame
            price_column: 用于计算涨跌额的价格列名，默认为'close'
            
        Returns:
            添加了涨跌额列的DataFrame，列名为'change_amount'
        """
        if data.empty:
            logger.warning("输入数据为空，无法计算涨跌额")
            return data
        
        if price_column not in data.columns:
            logger.error(f"数据中不存在列: {price_column}")
            return data
        
        result = data.copy()
        result['change_amount'] = result[price_column].diff()
        
        logger.debug("计算涨跌额完成")
        return result
    
    @staticmethod
    def calculate_volume_ma(data: pd.DataFrame, periods: Union[int, List[int]] = None) -> pd.DataFrame:
        """
        计算成交量移动平均
        
        Args:
            data: 包含成交量数据的DataFrame，必须包含'volume'列
            periods: 均量周期，可以是单个整数或整数列表，默认为[5, 10, 20]
            
        Returns:
            添加了均量列的DataFrame，列名格式为'volume_ma_5'等
        """
        if data.empty:
            logger.warning("输入数据为空，无法计算均量")
            return data
        
        if 'volume' not in data.columns:
            logger.error("数据中不存在'volume'列")
            return data
        
        # 默认计算5、10、20日均量
        if periods is None:
            periods = [5, 10, 20]
        elif isinstance(periods, int):
            periods = [periods]
        
        result = data.copy()
        
        for period in periods:
            col_name = f'volume_ma_{period}'
            result[col_name] = result['volume'].rolling(window=period, min_periods=1).mean()
            logger.debug(f"计算 {period} 日均量完成")
        
        return result
    
    @staticmethod
    def calculate_amplitude(data: pd.DataFrame) -> pd.DataFrame:
        """
        计算振幅（当日最高价和最低价之间的波动幅度）
        
        Args:
            data: 包含价格数据的DataFrame，必须包含'high', 'low', 'close'列
            
        Returns:
            添加了振幅列的DataFrame，列名为'amplitude'
        """
        if data.empty:
            logger.warning("输入数据为空，无法计算振幅")
            return data
        
        required_columns = ['high', 'low', 'close']
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            logger.error(f"数据中缺少列: {missing_columns}")
            return data
        
        result = data.copy()
        # 振幅 = (最高价 - 最低价) / 前一日收盘价 * 100
        prev_close = result['close'].shift(1)
        result['amplitude'] = ((result['high'] - result['low']) / prev_close * 100).fillna(0)
        
        logger.debug("计算振幅完成")
        return result
    
    @staticmethod
    def calculate_turnover_rate(data: pd.DataFrame, total_shares: Optional[float] = None) -> pd.DataFrame:
        """
        计算换手率
        
        Args:
            data: 包含成交量数据的DataFrame，必须包含'volume'列
            total_shares: 总股本（股），如果为None则无法计算换手率
            
        Returns:
            添加了换手率列的DataFrame，列名为'turnover_rate'
        """
        if data.empty:
            logger.warning("输入数据为空，无法计算换手率")
            return data
        
        if 'volume' not in data.columns:
            logger.error("数据中不存在'volume'列")
            return data
        
        result = data.copy()
        
        if total_shares is None or total_shares <= 0:
            logger.warning("未提供有效的总股本，换手率设为0")
            result['turnover_rate'] = 0
        else:
            # 换手率 = 成交量 / 总股本 * 100
            result['turnover_rate'] = (result['volume'] / total_shares * 100)
        
        logger.debug("计算换手率完成")
        return result
    
    @staticmethod
    def check_above_ma(data: pd.DataFrame, ma_period: int = 5, 
                       price_column: str = 'close', consecutive_days: int = 1) -> pd.DataFrame:
        """
        检查价格是否在均线之上
        
        Args:
            data: 包含价格和均线数据的DataFrame
            ma_period: 均线周期，默认为5
            price_column: 价格列名，默认为'close'
            consecutive_days: 连续天数，默认为1
            
        Returns:
            添加了检查结果列的DataFrame，列名为'above_ma_{period}'
        """
        if data.empty:
            logger.warning("输入数据为空，无法检查均线")
            return data
        
        ma_col = f'ma_{ma_period}'
        
        # 如果均线列不存在，先计算
        if ma_col not in data.columns:
            logger.info(f"均线列 {ma_col} 不存在，先计算均线")
            data = TechnicalIndicators.calculate_ma(data, periods=[ma_period], price_column=price_column)
        
        if price_column not in data.columns or ma_col not in data.columns:
            logger.error(f"缺少必要的列: {price_column} 或 {ma_col}")
            return data
        
        result = data.copy()
        
        # 检查是否在均线之上
        above = result[price_column] > result[ma_col]
        
        if consecutive_days > 1:
            # 检查连续N天在均线之上
            col_name = f'above_ma_{ma_period}_{consecutive_days}days'
            result[col_name] = above.rolling(window=consecutive_days, min_periods=consecutive_days).sum() == consecutive_days
        else:
            col_name = f'above_ma_{ma_period}'
            result[col_name] = above
        
        logger.debug(f"检查价格是否在 {ma_period} 日均线之上完成")
        return result
    
    @staticmethod
    def calculate_all_basic_indicators(data: pd.DataFrame) -> pd.DataFrame:
        """
        计算所有基础技术指标
        
        Args:
            data: 包含OHLCV数据的DataFrame
            
        Returns:
            添加了所有基础指标的DataFrame
        """
        if data.empty:
            logger.warning("输入数据为空，无法计算指标")
            return data
        
        logger.info("开始计算所有基础技术指标")
        
        result = data.copy()
        
        # 1. 计算移动平均线
        result = TechnicalIndicators.calculate_ma(result, periods=[5, 10, 20, 30, 60])
        
        # 2. 计算涨跌幅和涨跌额
        result = TechnicalIndicators.calculate_change_pct(result)
        result = TechnicalIndicators.calculate_change_amount(result)
        
        # 3. 计算成交量均线
        if 'volume' in result.columns:
            result = TechnicalIndicators.calculate_volume_ma(result, periods=[5, 10, 20])
        
        # 4. 计算振幅
        if all(col in result.columns for col in ['high', 'low', 'close']):
            result = TechnicalIndicators.calculate_amplitude(result)
        
        logger.info("所有基础技术指标计算完成")
        return result
    
    @staticmethod
    def find_big_rise_days(data: pd.DataFrame, threshold: float = 8.0, 
                          price_column: str = 'close') -> pd.DataFrame:
        """
        查找大涨日（涨幅超过阈值的交易日）
        
        Args:
            data: 包含价格数据的DataFrame
            threshold: 涨幅阈值（百分比），默认为8.0
            price_column: 价格列名，默认为'close'
            
        Returns:
            筛选出大涨日的DataFrame
        """
        if data.empty:
            logger.warning("输入数据为空，无法查找大涨日")
            return data
        
        # 如果没有涨跌幅列，先计算
        if 'change_pct' not in data.columns:
            data = TechnicalIndicators.calculate_change_pct(data, price_column=price_column)
        
        # 筛选涨幅超过阈值的交易日
        result = data[data['change_pct'] >= threshold].copy()
        
        logger.info(f"找到 {len(result)} 个涨幅超过 {threshold}% 的交易日")
        return result
