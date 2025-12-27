"""
Tushare数据源实现
"""
import pandas as pd
from typing import List, Optional
from datetime import datetime
from .datasource import DataSource
from app.utils import get_logger

logger = get_logger(__name__)


class TushareDataSource(DataSource):
    """Tushare数据源实现类"""
    
    def __init__(self, token: str):
        """
        初始化Tushare数据源
        
        Args:
            token: Tushare API token
        """
        if not token:
            raise ValueError("Tushare token不能为空")
        
        try:
            import tushare as ts
            self.ts = ts
            self.pro = ts.pro_api(token)
            logger.info("Tushare数据源初始化成功")
        except ImportError:
            logger.error("无法导入tushare模块，请先安装: pip install tushare")
            raise
    
    def get_stock_list(self) -> pd.DataFrame:
        """
        获取A股股票列表
        
        Returns:
            股票列表DataFrame
        """
        try:
            logger.info("正在从Tushare获取股票列表...")
            
            # 获取股票基本信息
            df = self.pro.stock_basic(
                exchange='',
                list_status='L',  # L=上市 D=退市 P=暂停上市
                fields='ts_code,symbol,name,area,industry,market,list_date'
            )
            
            # 标准化列名
            df = df.rename(columns={
                'symbol': 'code',
                'name': 'name',
                'list_date': 'list_date',
                'industry': 'industry',
                'market': 'market_type'
            })
            
            # 转换市场类型
            market_map = {
                '主板': '主板',
                '创业板': '创业板',
                '科创板': '科创板',
                '北交所': '北交所'
            }
            df['market_type'] = df['market_type'].map(market_map).fillna('其他')
            df['status'] = 'normal'
            
            # 选择需要的列
            df = df[['code', 'name', 'list_date', 'industry', 'market_type', 'status']]
            
            logger.info(f"成功获取{len(df)}只股票信息")
            return df
            
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            raise
    
    def get_daily_data(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取股票日线行情数据（别名方法，兼容其他数据源）
        
        Args:
            code: 股票代码
            start_date: 开始日期（YYYY-MM-DD）
            end_date: 结束日期（YYYY-MM-DD）
            
        Returns:
            行情数据DataFrame
        """
        return self.get_stock_daily(code, start_date, end_date)
    
    def get_stock_daily(self, stock_code: str, start_date: str = None, 
                       end_date: str = None) -> pd.DataFrame:
        """
        获取股票日线行情数据
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期（YYYY-MM-DD）
            end_date: 结束日期（YYYY-MM-DD）
            
        Returns:
            行情数据DataFrame
        """
        try:
            # 标准化股票代码（Tushare需要带后缀）
            code = self.normalize_stock_code(stock_code)
            if code.startswith('6'):
                ts_code = f"{code}.SH"
            else:
                ts_code = f"{code}.SZ"
            
            # 转换日期格式（Tushare使用YYYYMMDD格式）
            start = start_date.replace('-', '') if start_date else '19900101'
            end = end_date.replace('-', '') if end_date else datetime.now().strftime('%Y%m%d')
            
            # 获取历史行情数据
            df = self.pro.daily(
                ts_code=ts_code,
                start_date=start,
                end_date=end
            )
            
            if df.empty:
                logger.warning(f"股票{code}没有行情数据")
                return pd.DataFrame()
            
            # 标准化列名为数据库表结构需要的列名
            df = df.rename(columns={
                'trade_date': 'trade_date',
                'open': 'open',
                'close': 'close',
                'high': 'high',
                'low': 'low',
                'vol': 'volume',
                'amount': 'amount',
                'pct_chg': 'change_pct'
            })
            
            # 添加股票代码（不带后缀）
            df['code'] = code
            
            # 转换日期格式
            df['trade_date'] = pd.to_datetime(df['trade_date']).dt.strftime('%Y-%m-%d')
            
            # 成交量单位转换（Tushare单位是手，转换为股）
            df['volume'] = df['volume'] * 100
            
            # 成交额单位转换（Tushare单位是千元，转换为元）
            df['amount'] = df['amount'] * 1000
            
            # 选择需要的列，使用与数据库表结构匹配的列名
            columns = ['code', 'trade_date', 'open', 'close', 
                      'high', 'low', 'volume', 'amount', 'change_pct']
            df = df[[col for col in columns if col in df.columns]]
            
            # 按日期升序排列
            df = df.sort_values('trade_date')
            
            return df
            
        except Exception as e:
            logger.error(f"获取股票{stock_code}行情数据失败: {e}")
            raise
    
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
        try:
            # 转换日期格式
            start = start_date.replace('-', '') if start_date else '19900101'
            end = end_date.replace('-', '') if end_date else datetime.now().strftime('%Y%m%d')
            
            # 获取交易日历
            df = self.pro.trade_cal(
                exchange='SSE',
                start_date=start,
                end_date=end,
                is_open='1'  # 1=交易日 0=非交易日
            )
            
            # 转换日期格式
            df['cal_date'] = pd.to_datetime(df['cal_date']).dt.strftime('%Y-%m-%d')
            
            return df['cal_date'].tolist()
            
        except Exception as e:
            logger.error(f"获取交易日历失败: {e}")
            return []
    
    def is_trading_day(self, date: str) -> bool:
        """
        判断是否为交易日
        
        Args:
            date: 日期（YYYY-MM-DD）
            
        Returns:
            是否为交易日
        """
        try:
            trading_dates = self.get_trading_dates(
                start_date=date,
                end_date=date
            )
            return date in trading_dates
        except Exception as e:
            logger.error(f"判断交易日失败: {e}")
            # 简单判断：周一到周五
            dt = datetime.strptime(date, '%Y-%m-%d')
            return dt.weekday() < 5
