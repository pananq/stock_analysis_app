"""
股票基础数据管理服务
负责股票列表的获取、存储和查询
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd
from app.models.database_factory import get_database
from app.services.datasource_factory import get_datasource
from app.services.market_identity import normalize_security_code
from app.services.security_list_service import SecurityListService
from app.utils import get_logger, get_rate_limiter

logger = get_logger(__name__)


class StockService:
    """股票基础数据管理服务类"""
    
    def __init__(
        self,
        db=None,
        datasource=None,
        security_list_service=None,
        rate_limiter=None,
    ):
        """初始化股票服务"""
        self.db = db or get_database()
        self.datasource = datasource or get_datasource()
        self.security_list_service = (
            security_list_service or SecurityListService()
        )
        self.rate_limiter = rate_limiter or get_rate_limiter()
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
            # A股沿用主数据源；港股、美股使用交易所官方清单。
            self.rate_limiter.wait()
            (
                df,
                market_counts,
                market_errors,
                loaded_scopes,
            ) = self._fetch_all_stock_lists()
            
            if df.empty:
                logger.warning("未获取到股票数据")
                self._update_history_status(update_id, 'failed', 0, 0, 0, '未获取到股票数据')
                return {
                    'success': False,
                    'message': '未获取到股票数据',
                    'total': 0
                }
            
            logger.info(
                "获取到%s只股票信息，分市场统计: %s",
                len(df),
                market_counts,
            )
            
            # 准备批量插入数据
            success_count = 0
            fail_count = 0
            
            # 保留证券ID：先把成功加载的目录范围标记为 inactive，
            # 再通过 upsert 重新激活仍存在的证券。
            self._mark_loaded_scopes_inactive(loaded_scopes)
            
            # 批量插入
            insert_data = []
            for _, row in df.iterrows():
                try:
                    stock_data = {
                        'market': self._market_from_row(row),
                        'code': row.get('code', ''),
                        'name': row.get('name', ''),
                        'list_date': row.get('list_date', None),
                        'industry': row.get('industry', None),
                        'market_type': row.get('market_type', None),
                        'security_type': row.get('security_type', 'STOCK'),
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
                    INSERT INTO stocks
                        (market, code, name, list_date, industry, market_type,
                         security_type, status, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        name = VALUES(name),
                        list_date = VALUES(list_date),
                        industry = VALUES(industry),
                        market_type = VALUES(market_type),
                        status = VALUES(status),
                        updated_at = VALUES(updated_at)
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
                'message': (
                    '股票列表更新成功'
                    if not market_errors
                    else '股票列表部分更新成功，失败市场已保留旧数据'
                ),
                'total': len(df),
                'success_count': success_count,
                'fail_count': fail_count,
                'duration': duration,
                'markets': market_counts,
                'market_errors': market_errors,
                'security_types': self._count_security_types(df),
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
            # 同时获取 A股、港股和美股最新代码列表。
            self.rate_limiter.wait()
            (
                df,
                market_counts,
                market_errors,
                _loaded_scopes,
            ) = self._fetch_all_stock_lists()
            
            if df.empty:
                logger.warning("未获取到股票数据")
                self._update_history_status(update_id, 'failed', 0, 0, 0, '未获取到股票数据')
                return {
                    'success': False,
                    'message': '未获取到股票数据',
                    'total': 0
                }
            
            existing_stocks = self.db.execute_query(
                "SELECT market, code, security_type FROM stocks"
            )
            existing_keys = {
                (
                    stock['market'],
                    stock['code'],
                    stock.get('security_type') or 'STOCK',
                )
                for stock in existing_stocks
            }
            
            new_count = 0
            update_count = 0
            upsert_data = []
            seen_keys = set()
            
            # 处理每只股票
            for _, row in df.iterrows():
                code = row.get('code', '')
                market = self._market_from_row(row)
                security_type = str(
                    row.get('security_type') or 'STOCK'
                ).upper()
                key = (market, code, security_type)
                if not code or key in seen_keys:
                    continue
                seen_keys.add(key)
                
                stock_data = {
                    'market': market,
                    'code': code,
                    'name': row.get('name', ''),
                    'list_date': row.get('list_date', None),
                    'industry': row.get('industry', None),
                    'market_type': row.get('market_type', None),
                    'security_type': security_type,
                    'status': row.get('status', 'normal'),
                    'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                upsert_data.append(tuple(stock_data.values()))
                
                if key in existing_keys:
                    update_count += 1
                else:
                    new_count += 1

            if upsert_data:
                self.db.execute_many(
                    '''
                    INSERT INTO stocks
                        (market, code, name, list_date, industry, market_type,
                         security_type, status, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        name = VALUES(name),
                        list_date = VALUES(list_date),
                        industry = VALUES(industry),
                        market_type = VALUES(market_type),
                        status = VALUES(status),
                        updated_at = VALUES(updated_at)
                    ''',
                    upsert_data,
                )
            
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
                'message': (
                    '股票列表增量更新成功'
                    if not market_errors
                    else '股票列表部分更新成功，失败市场已跳过'
                ),
                'total': len(df),
                'new_count': new_count,
                'update_count': update_count,
                'duration': duration,
                'markets': market_counts,
                'market_errors': market_errors,
                'security_types': self._count_security_types(df),
            }
            
        except Exception as e:
            logger.error(f"增量更新股票列表失败: {e}")
            self._update_history_status(update_id, 'failed', 0, 0, 0, str(e))
            return {
                'success': False,
                'message': f'增量更新失败: {e}',
                'total': 0
            }
    
    def get_stock_list(
        self,
        market_type: str = None,
        security_type: str = None,
        industry: str = None,
        status: str = 'normal',
        limit: int = None,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
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
        
        query, params = self._append_market_filter(
            query,
            params,
            market_type,
        )
        if security_type:
            query += " AND security_type = %s"
            params.append(str(security_type).upper())
        if industry:
            query += " AND industry LIKE %s"
            params.append(f"%{industry.strip()}%")
        
        if status:
            query += " AND status = %s"
            params.append(status)
        
        query += " ORDER BY code"
        
        if limit:
            query += f" LIMIT {limit} OFFSET {offset}"
        
        rows = self.db.execute_query(
            query,
            tuple(params) if params else None,
        )
        return [self._decorate_market(row) for row in rows]
    
    def get_stock_by_code(
        self,
        code: str,
        market: str = None,
        security_type: str = None,
    ) -> Optional[Dict[str, Any]]:
        """
        根据股票代码查询股票信息
        
        Args:
            code: 股票代码
            
        Returns:
            股票信息字典，如果不存在则返回None
        """
        query = "SELECT * FROM stocks WHERE code = %s"
        params = [code]
        query, params = self._append_market_filter(query, params, market)
        if security_type:
            query += " AND security_type = %s"
            params.append(str(security_type).upper())
        result = self.db.execute_query(
            query,
            tuple(params),
        )
        if len(result) > 1 and (not market or not security_type):
            raise ValueError(
                "证券代码在多个市场或类型中存在，请同时指定 market "
                "和 security_type"
            )
        return self._decorate_market(result[0]) if result else None
    
    def search_stocks(
        self,
        keyword: str,
        limit: int = 20,
        market: str = None,
        security_type: str = None,
        industry: str = None,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
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
            WHERE (code LIKE %s OR name LIKE %s)
        """
        keyword_pattern = f"%{keyword}%"
        params = [keyword_pattern, keyword_pattern]
        query, params = self._append_market_filter(query, params, market)
        if security_type:
            query += " AND security_type = %s"
            params.append(str(security_type).upper())
        if industry:
            query += " AND industry LIKE %s"
            params.append(f"%{industry.strip()}%")
        # 精确代码命中优先，避免搜索 QQQ 时先被 CQQQ、DVQQ 等
        # 包含匹配占满当前页。
        query += (
            " ORDER BY CASE WHEN UPPER(code) = UPPER(%s) "
            "THEN 0 ELSE 1 END, code LIMIT %s OFFSET %s"
        )
        params.append(keyword.strip())
        params.append(limit)
        params.append(offset)
        rows = self.db.execute_query(query, tuple(params))
        return [self._decorate_market(row) for row in rows]
    
    def get_stock_count(
        self,
        market_type: str = None,
        security_type: str = None,
        industry: str = None,
    ) -> int:
        """
        获取股票数量
        
        Args:
            market_type: 市场类型筛选
            
        Returns:
            股票数量
        """
        query = "SELECT COUNT(*) as count FROM stocks WHERE 1=1"
        params = []
        
        query, params = self._append_market_filter(
            query,
            params,
            market_type,
        )
        if security_type:
            query += " AND security_type = %s"
            params.append(str(security_type).upper())
        if industry:
            query += " AND industry LIKE %s"
            params.append(f"%{industry.strip()}%")
        
        result = self.db.execute_query(query, tuple(params) if params else None)
        return result[0]['count'] if result else 0
    
    def get_market_types(self) -> List[str]:
        """
        获取所有市场类型
        
        Returns:
            市场类型列表
        """
        result = self.db.execute_query(
            "SELECT DISTINCT market FROM stocks WHERE market IS NOT NULL"
        )
        return [row['market'] for row in result]
    
    def list_stocks(self, market: str = None, keyword: str = None,
                   security_type: str = None, industry: str = None,
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
            return self.search_stocks(
                keyword,
                limit=limit,
                market=market,
                security_type=security_type,
                industry=industry,
                offset=offset,
            )
        else:
            # 否则使用列表查询
            return self.get_stock_list(
                market_type=market,
                security_type=security_type,
                industry=industry,
                limit=limit,
                offset=offset,
            )
    
    def count_stocks(
        self,
        market: str = None,
        keyword: str = None,
        security_type: str = None,
        industry: str = None,
    ) -> int:
        """
        获取股票数量（API接口使用）
        
        Args:
            market: 市场类型筛选
            keyword: 搜索关键词
            
        Returns:
            股票数量
        """
        query = "SELECT COUNT(*) AS count FROM stocks WHERE 1=1"
        params = []
        if keyword:
            query += " AND (code LIKE %s OR name LIKE %s)"
            keyword_pattern = f"%{keyword}%"
            params.extend([keyword_pattern, keyword_pattern])
        query, params = self._append_market_filter(query, params, market)
        if security_type:
            query += " AND security_type = %s"
            params.append(str(security_type).upper())
        if industry:
            query += " AND industry LIKE %s"
            params.append(f"%{industry.strip()}%")
        result = self.db.execute_query(
            query,
            tuple(params) if params else None,
        )
        return result[0]['count'] if result else 0
    
    def get_stock(
        self,
        stock_code: str,
        market: str = None,
        security_type: str = None,
    ) -> Optional[Dict[str, Any]]:
        """
        获取股票详情（API接口使用）
        
        Args:
            stock_code: 股票代码
            
        Returns:
            股票信息
        """
        return self.get_stock_by_code(
            stock_code,
            market=market,
            security_type=security_type,
        )

    def _fetch_all_stock_lists(self):
        parts = {}
        market_errors = {}
        try:
            cn_frame = self._standardize_cn_list(
                self.datasource.get_stock_list()
            )
            if cn_frame.empty:
                raise ValueError("A 股股票列表为空")
            parts['CN_STOCK'] = cn_frame
        except Exception as exc:
            market_errors['CN'] = str(exc)
            logger.warning("获取 CN 股票列表失败，将保留旧数据: %s", exc)

        if hasattr(self.security_list_service, 'get_catalog_parts'):
            catalog_parts, catalog_errors = (
                self.security_list_service.get_catalog_parts()
            )
            parts.update(catalog_parts)
            market_errors.update(catalog_errors)
        else:
            global_frames, global_errors = (
                self.security_list_service.get_global_stock_lists()
            )
            for market, frame in global_frames.items():
                frame = frame.copy()
                if 'security_type' not in frame:
                    frame['security_type'] = 'STOCK'
                for security_type, group in frame.groupby('security_type'):
                    parts[f'{market}_{security_type}'] = group
            market_errors.update(global_errors)
        if not parts:
            raise ValueError("所有市场的股票列表均获取失败")
        combined = pd.concat(parts.values(), ignore_index=True)
        market_counts = {
            market: int(count)
            for market, count in (
                combined.assign(
                    _market=combined['market_type'].map(
                        lambda value: (
                            value if value in {'HK', 'US'} else 'CN'
                        )
                    )
                )
                .groupby('_market')
                .size()
                .items()
            )
        }
        return combined, market_counts, market_errors, set(parts)

    @staticmethod
    def _standardize_cn_list(frame: pd.DataFrame) -> pd.DataFrame:
        rows = []
        for _, row in frame.iterrows():
            try:
                code = normalize_security_code(str(row.get('code', '')), 'CN')
            except ValueError:
                continue
            rows.append({
                'code': code,
                'name': str(row.get('name', '')).strip(),
                'list_date': row.get('list_date', None),
                'industry': row.get('industry', None),
                'market_type': row.get('market_type', None) or 'CN',
                'security_type': 'STOCK',
                'status': row.get('status', 'normal'),
            })
        return pd.DataFrame(rows)

    def _mark_loaded_scopes_inactive(self, loaded_scopes):
        for scope in sorted(loaded_scopes):
            market, security_type = scope.split('_', 1)
            self.db.execute_update(
                "UPDATE stocks SET status = 'inactive', updated_at = %s "
                "WHERE market = %s AND security_type = %s",
                (
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    market,
                    security_type,
                ),
            )
        logger.info("已标记待刷新的证券目录范围: %s", sorted(loaded_scopes))

    def _clear_loaded_scopes(self, loaded_scopes):
        """兼容旧调用；不再删除证券记录。"""
        self._mark_loaded_scopes_inactive(loaded_scopes)

    @staticmethod
    def _append_market_filter(query, params, market):
        if not market:
            return query, params
        value = str(market).strip().upper()
        query += " AND market = %s"
        params.append(value)
        return query, params

    @staticmethod
    def _decorate_market(row):
        decorated = dict(row)
        decorated['market'] = str(
            decorated.get('market') or 'CN'
        ).upper()
        decorated['security_id'] = decorated.get('id')
        decorated['security_type'] = (
            str(decorated.get('security_type') or 'STOCK').upper()
        )
        return decorated

    @staticmethod
    def _market_from_row(row):
        explicit = str(row.get('market') or '').strip().upper()
        if explicit in {'CN', 'HK', 'US'}:
            return explicit
        market_type = str(row.get('market_type') or '').strip().upper()
        return market_type if market_type in {'HK', 'US'} else 'CN'

    @staticmethod
    def _count_security_types(frame):
        return {
            security_type: int(count)
            for security_type, count in (
                frame['security_type'].fillna('STOCK').value_counts().items()
            )
        }
    
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
