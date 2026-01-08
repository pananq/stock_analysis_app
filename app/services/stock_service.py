"""
股票基础数据管理服务
负责股票列表的获取、存储和查询
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd
from app.models.database_factory import get_database
from app.services import get_datasource
from app.utils import get_logger, get_rate_limiter

logger = get_logger(__name__)


class StockService:
    """股票基础数据管理服务类"""
    
    def __init__(self):
        """初始化股票服务"""
        self.db = get_database()
        self.datasource = get_datasource()
        self.rate_limiter = get_rate_limiter()
        logger.info("股票服务初始化完成")
    
    def fetch_and_save_stock_list(self) -> Dict[str, Any]:
        """
        从数据源获取股票列表并保存到数据库（全量更新）
        
        Returns:
            包含执行结果的字典
        """
        logger.info("开始获取股票列表...")
        start_time = datetime.now()
        
        # 记录更新历史
        update_id = self.db.insert_one('data_update_history', {
            'update_type': 'stock_list_full',
            'start_time': start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'running'
        })
        
        try:
            # 从数据源获取股票列表
            self.rate_limiter.wait()
            df = self.datasource.get_stock_list()
            
            if df.empty:
                logger.warning("未获取到股票数据")
                self._update_history_status(update_id, 'failed', 0, 0, 0, '未获取到股票数据')
                return {
                    'success': False,
                    'message': '未获取到股票数据',
                    'total': 0
                }
            
            logger.info(f"获取到{len(df)}只股票信息")
            
            # 准备批量插入数据
            success_count = 0
            fail_count = 0
            
            # 清空现有数据（全量更新）
            self.db.execute_update("DELETE FROM stocks")
            logger.info("已清空现有股票数据")
            
            # 批量插入
            insert_data = []
            for _, row in df.iterrows():
                try:
                    stock_data = {
                        'code': row.get('code', ''),
                        'name': row.get('name', ''),
                        'list_date': row.get('list_date', None),
                        'industry': row.get('industry', None),
                        'market_type': row.get('market_type', None),
                        'status': row.get('status', 'normal'),
                        'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    insert_data.append(tuple(stock_data.values()))
                    success_count += 1
                except Exception as e:
                    logger.error(f"准备股票数据失败 {row.get('code', 'unknown')}: {e}")
                    fail_count += 1
            
            # 执行批量插入
            if insert_data:
                query = '''
                    INSERT INTO stocks (code, name, list_date, industry, market_type, status, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                '''
                self.db.execute_many(query, insert_data)
                logger.info(f"成功插入{success_count}条股票数据")
            
            # 更新历史记录
            end_time = datetime.now()
            self._update_history_status(
                update_id, 'completed', len(df), success_count, fail_count,
                end_time=end_time.strftime('%Y-%m-%d %H:%M:%S')
            )
            
            duration = (end_time - start_time).total_seconds()
            logger.info(f"股票列表更新完成，耗时{duration:.2f}秒")
            
            return {
                'success': True,
                'message': '股票列表更新成功',
                'total': len(df),
                'success_count': success_count,
                'fail_count': fail_count,
                'duration': duration
            }
            
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            self._update_history_status(update_id, 'failed', 0, 0, 0, str(e))
            return {
                'success': False,
                'message': f'获取股票列表失败: {e}',
                'total': 0
            }
    
    def update_stock_list(self) -> Dict[str, Any]:
        """
        增量更新股票列表（只更新变化的数据）
        
        Returns:
            包含执行结果的字典
        """
        logger.info("开始增量更新股票列表...")
        start_time = datetime.now()
        
        # 记录更新历史
        update_id = self.db.insert_one('data_update_history', {
            'update_type': 'stock_list_incremental',
            'start_time': start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'running'
        })
        
        try:
            # 从数据源获取最新股票列表
            self.rate_limiter.wait()
            df = self.datasource.get_stock_list()
            
            if df.empty:
                logger.warning("未获取到股票数据")
                self._update_history_status(update_id, 'failed', 0, 0, 0, '未获取到股票数据')
                return {
                    'success': False,
                    'message': '未获取到股票数据',
                    'total': 0
                }
            
            # 获取现有股票代码
            existing_stocks = self.db.execute_query("SELECT code FROM stocks")
            existing_codes = {stock['code'] for stock in existing_stocks}
            
            new_count = 0
            update_count = 0
            
            # 处理每只股票
            for _, row in df.iterrows():
                code = row.get('code', '')
                
                stock_data = {
                    'code': code,
                    'name': row.get('name', ''),
                    'list_date': row.get('list_date', None),
                    'industry': row.get('industry', None),
                    'market_type': row.get('market_type', None),
                    'status': row.get('status', 'normal'),
                    'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                if code in existing_codes:
                    # 更新现有股票
                    self.db.update_one('stocks', 
                                      {k: v for k, v in stock_data.items() if k != 'code'},
                                      {'code': code})
                    update_count += 1
                else:
                    # 插入新股票
                    self.db.insert_one('stocks', stock_data)
                    new_count += 1
            
            # 更新历史记录
            end_time = datetime.now()
            self._update_history_status(
                update_id, 'completed', len(df), new_count + update_count, 0,
                end_time=end_time.strftime('%Y-%m-%d %H:%M:%S')
            )
            
            duration = (end_time - start_time).total_seconds()
            logger.info(f"股票列表增量更新完成，新增{new_count}只，更新{update_count}只，耗时{duration:.2f}秒")
            
            return {
                'success': True,
                'message': '股票列表增量更新成功',
                'total': len(df),
                'new_count': new_count,
                'update_count': update_count,
                'duration': duration
            }
            
        except Exception as e:
            logger.error(f"增量更新股票列表失败: {e}")
            self._update_history_status(update_id, 'failed', 0, 0, 0, str(e))
            return {
                'success': False,
                'message': f'增量更新失败: {e}',
                'total': 0
            }
    
    def get_stock_list(self, market_type: str = None, status: str = 'normal',
                      limit: int = None, offset: int = 0) -> List[Dict[str, Any]]:
        """
        查询股票列表
        
        Args:
            market_type: 市场类型筛选
            status: 状态筛选
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            股票列表
        """
        query = "SELECT * FROM stocks WHERE 1=1"
        params = []
        
        if market_type:
            query += " AND market_type = ?"
            params.append(market_type)
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY code"
        
        if limit:
            query += f" LIMIT {limit} OFFSET {offset}"
        
        return self.db.execute_query(query, tuple(params) if params else None)
    
    def get_stock_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        """
        根据股票代码查询股票信息
        
        Args:
            code: 股票代码
            
        Returns:
            股票信息字典，如果不存在则返回None
        """
        result = self.db.execute_query(
            "SELECT * FROM stocks WHERE code = %s",
            (code,)
        )
        return result[0] if result else None
    
    def search_stocks(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        搜索股票（按代码或名称）
        
        Args:
            keyword: 搜索关键词
            limit: 返回数量限制
            
        Returns:
            股票列表
        """
        query = """
            SELECT * FROM stocks
            WHERE code LIKE %s OR name LIKE %s
            ORDER BY code
            LIMIT %s
        """
        keyword_pattern = f"%{keyword}%"
        return self.db.execute_query(query, (keyword_pattern, keyword_pattern, limit))
    
    def get_stock_count(self, market_type: str = None) -> int:
        """
        获取股票数量
        
        Args:
            market_type: 市场类型筛选
            
        Returns:
            股票数量
        """
        query = "SELECT COUNT(*) as count FROM stocks WHERE 1=1"
        params = []
        
        if market_type:
            query += " AND market_type = ?"
            params.append(market_type)
        
        result = self.db.execute_query(query, tuple(params) if params else None)
        return result[0]['count'] if result else 0
    
    def get_market_types(self) -> List[str]:
        """
        获取所有市场类型
        
        Returns:
            市场类型列表
        """
        result = self.db.execute_query(
            "SELECT DISTINCT market_type FROM stocks WHERE market_type IS NOT NULL"
        )
        return [row['market_type'] for row in result]
    
    def list_stocks(self, market: str = None, keyword: str = None,
                   limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        查询股票列表（API接口使用）
        
        Args:
            market: 市场类型筛选
            keyword: 搜索关键词
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            股票列表
        """
        if keyword:
            # 如果有关键词，使用搜索
            return self.search_stocks(keyword, limit=limit)
        else:
            # 否则使用列表查询
            return self.get_stock_list(market_type=market, limit=limit, offset=offset)
    
    def count_stocks(self, market: str = None, keyword: str = None) -> int:
        """
        获取股票数量（API接口使用）
        
        Args:
            market: 市场类型筛选
            keyword: 搜索关键词
            
        Returns:
            股票数量
        """
        if keyword:
            # 如果有关键词，返回搜索结果数量
            results = self.search_stocks(keyword, limit=10000)
            return len(results)
        else:
            # 否则返回总数
            return self.get_stock_count(market_type=market)
    
    def get_stock(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        获取股票详情（API接口使用）
        
        Args:
            stock_code: 股票代码
            
        Returns:
            股票信息
        """
        return self.get_stock_by_code(stock_code)
    
    def _update_history_status(self, update_id: int, status: str, 
                              total_count: int, success_count: int, 
                              fail_count: int, error_message: str = None,
                              end_time: str = None):
        """
        更新数据更新历史记录状态
        
        Args:
            update_id: 更新记录ID
            status: 状态
            total_count: 总数
            success_count: 成功数
            fail_count: 失败数
            error_message: 错误信息
            end_time: 结束时间
        """
        update_data = {
            'status': status,
            'total_count': total_count,
            'success_count': success_count,
            'fail_count': fail_count
        }
        
        if end_time:
            update_data['end_time'] = end_time
        
        if error_message:
            update_data['error_message'] = error_message
        
        self.db.update_one('data_update_history', update_data, {'id': update_id})


# 全局服务实例
_stock_service_instance: Optional[StockService] = None


def get_stock_service() -> StockService:
    """
    获取全局股票服务实例
    
    Returns:
        StockService实例
    """
    global _stock_service_instance
    if _stock_service_instance is None:
        _stock_service_instance = StockService()
    return _stock_service_instance
