"""
Akshare数据源实现
"""
import pandas as pd
from typing import List, Optional
from datetime import datetime
from .datasource import DataSource
from app.utils import get_logger

logger = get_logger(__name__)


class AkshareDataSource(DataSource):
    """Akshare数据源实现类"""
    
    def __init__(self):
        """初始化Akshare数据源"""
        try:
            import akshare as ak
            self.ak = ak
            logger.info("Akshare数据源初始化成功")
        except ImportError:
            logger.error("无法导入akshare模块，请先安装: pip install akshare")
            raise
    
    def get_stock_list(self) -> pd.DataFrame:
        """
        获取A股股票列表
        
        Returns:
            股票列表DataFrame
        """
        try:
            logger.info("正在从Akshare获取股票列表...")
            
            # 使用更稳定的API获取股票列表
            # 获取沪深A股实时行情数据（包含所有股票）
            df = self.ak.stock_zh_a_spot_em()
            
            # 标准化列名
            df = df.rename(columns={
                '代码': 'code',
                '名称': 'name'
            })
            
            # 只保留需要的列
            df = df[['code', 'name']]
            
            # 添加市场类型
            def get_market_type(code):
                if code.startswith('688'):
                    return '科创板'
                elif code.startswith('300'):
                    return '创业板'
                elif code.startswith('60'):
                    return '沪市主板'
                elif code.startswith('00'):
                    return '深市主板'
                elif code.startswith('8'):
                    return '北交所'
                else:
                    return '其他'
            
            df['market_type'] = df['code'].apply(get_market_type)
            df['list_date'] = None  # akshare基础接口不提供上市日期
            df['industry'] = None   # akshare基础接口不提供行业信息
            df['status'] = 'normal'
            
            logger.info(f"成功获取{len(df)}只股票信息")
            return df
            
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            raise
    
    def get_daily_data(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取股票日线行情数据
        
        Args:
            code: 股票代码
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            日线行情DataFrame
        """
        try:
            logger.info(f"正在从Akshare获取{code}的历史行情数据...")
            
            # 使用akshare获取个股历史行情数据
            df = self.ak.stock_zh_a_hist(symbol=code, start_date=start_date.replace('-', ''), 
                                        end_date=end_date.replace('-', ''), adjust="qfq")
            
            if df.empty:
                logger.warning(f"股票{code}未获取到数据")
                return pd.DataFrame()
            
            # 标准化列名
            df = df.rename(columns={
                '日期': 'trade_date',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume',
                '成交额': 'amount',
                '涨跌幅': 'change_pct',
                '换手率': 'turnover_rate'
            })
            
            # 只保留需要的列
            columns = ['trade_date', 'open', 'close', 'high', 'low', 'volume', 'amount', 'change_pct', 'turnover_rate']
            df = df[[col for col in columns if col in df.columns]]
            
            # 添加股票代码
            df['code'] = code
            
            # 转换日期格式
            df['trade_date'] = pd.to_datetime(df['trade_date']).dt.date
            
            logger.info(f"成功获取{code}的{len(df)}条历史行情数据")
            return df
            
        except Exception as e:
            logger.error(f"获取{code}历史行情失败: {e}")
            return pd.DataFrame()
    
    def get_stock_daily(self, stock_code: str, start_date: str = None, 
                       end_date: str = None) -> pd.DataFrame:
        """
        获取股票日线行情数据
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            行情数据DataFrame
        """
        try:
            # 标准化股票代码
            code = self.normalize_stock_code(stock_code)
            
            # 获取历史行情数据
            df = self.ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date=start_date.replace('-', '') if start_date else "19900101",
                end_date=end_date.replace('-', '') if end_date else datetime.now().strftime('%Y%m%d'),
                adjust="qfq"  # 前复权
            )
            
            if df.empty:
                logger.warning(f"股票{code}没有行情数据")
                return pd.DataFrame()
            
            # 标准化列名为数据库表结构需要的列名
            df = df.rename(columns={
                '日期': 'trade_date',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume',
                '成交额': 'amount',
                '涨跌幅': 'change_pct'
            })
            
            # 添加股票代码
            df['code'] = code
            
            # 选择需要的列，使用与数据库表结构匹配的列名
            columns = ['code', 'trade_date', 'open', 'close', 
                      'high', 'low', 'volume', 'amount', 'change_pct']
            df = df[[col for col in columns if col in df.columns]]
            
            # 转换日期格式
            df['trade_date'] = pd.to_datetime(df['trade_date']).dt.strftime('%Y-%m-%d')
            
            return df
            
        except Exception as e:
            logger.error(f"获取股票{stock_code}行情数据失败: {e}")
            raise
    
    def get_trading_dates(self, start_date: str = None, 
                         end_date: str = None) -> List[str]:
        """
        获取交易日历
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            交易日期列表
        """
        try:
            # 获取交易日历
            df = self.ak.tool_trade_date_hist_sina()
            
            # 转换日期格式
            df['trade_date'] = pd.to_datetime(df['trade_date']).dt.strftime('%Y-%m-%d')
            
            # 筛选日期范围
            if start_date:
                df = df[df['trade_date'] >= start_date]
            if end_date:
                df = df[df['trade_date'] <= end_date]
            
            return df['trade_date'].tolist()
            
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
            # 获取最近的交易日历
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
