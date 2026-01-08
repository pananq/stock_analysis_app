"""
股票查询API路由

提供股票数据查询和管理功能
"""

from flask import Blueprint, request, jsonify
from app.services import get_stock_service, get_market_data_service
from app.utils import get_logger

logger = get_logger(__name__)

stock_bp = Blueprint('stock', __name__)


@stock_bp.route('', methods=['GET'])
def list_stocks():
    """
    获取股票列表
    
    Query参数:
        market: 市场类型（SH/SZ/BJ）
        keyword: 搜索关键词（股票代码或名称）
        limit: 返回记录数（默认100）
        offset: 偏移量（默认0）
        
    Returns:
        股票列表
    """
    try:
        market = request.args.get('market')
        keyword = request.args.get('keyword')
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        
        stock_service = get_stock_service()
        stocks = stock_service.list_stocks(
            market=market,
            keyword=keyword,
            limit=limit,
            offset=offset
        )
        
        total = stock_service.count_stocks(market=market, keyword=keyword)
        
        return jsonify({
            'success': True,
            'data': stocks,
            'pagination': {
                'total': total,
                'limit': limit,
                'offset': offset,
                'has_more': offset + len(stocks) < total
            }
        })
        
    except Exception as e:
        logger.error(f"获取股票列表失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@stock_bp.route('/<string:stock_code>', methods=['GET'])
def get_stock(stock_code):
    """
    获取股票详情
    
    Args:
        stock_code: 股票代码
        
    Returns:
        股票详情
    """
    try:
        stock_service = get_stock_service()
        stock = stock_service.get_stock(stock_code)
        
        if stock:
            # 添加兼容字段，同时支持 name/code 和 stock_name/stock_code
            if 'name' in stock and 'stock_name' not in stock:
                stock['stock_name'] = stock['name']
            if 'code' in stock and 'stock_code' not in stock:
                stock['stock_code'] = stock['code']
                
            return jsonify({
                'success': True,
                'data': stock
            })
        else:
            return jsonify({
                'success': False,
                'error': '股票不存在'
            }), 404
            
    except Exception as e:
        logger.error(f"获取股票详情失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@stock_bp.route('/<string:stock_code>/history', methods=['GET'])
def get_stock_history_data(stock_code):
    """
    获取股票历史数据（兼容前端调用）
    
    Args:
        stock_code: 股票代码
        
    Query参数:
        start_date: 开始日期（YYYY-MM-DD）
        end_date: 结束日期（YYYY-MM-DD）
        limit: 返回记录数（默认100）
        
    Returns:
        历史数据列表
    """
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = int(request.args.get('limit', 100))
        
        market_data_service = get_market_data_service()
        df = market_data_service.get_stock_data(
            code=stock_code,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        
        # 将DataFrame转换为字典列表，并映射字段名以兼容前端
        data = []
        if not df.empty:
            # 重命名列以匹配前端期望的字段名
            df_renamed = df.rename(columns={
                'open': 'open_price',
                'close': 'close_price',
                'high': 'high_price',
                'low': 'low_price'
            })
            # 将NaN替换为None以生成有效的JSON
            df_renamed = df_renamed.astype(object).where(df_renamed.notna(), None)
            data = df_renamed.to_dict('records')
        
        return jsonify({
            'success': True,
            'data': data,
            'count': len(data)
        })
        
    except Exception as e:
        logger.error(f"获取历史数据失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@stock_bp.route('/<string:stock_code>/daily', methods=['GET'])
def get_stock_daily_data(stock_code):
    """
    获取股票日线数据
    
    Args:
        stock_code: 股票代码
        
    Query参数:
        start_date: 开始日期（YYYY-MM-DD）
        end_date: 结束日期（YYYY-MM-DD）
        limit: 返回记录数（默认100）
        
    Returns:
        日线数据列表
    """
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = int(request.args.get('limit', 100))
        
        market_data_service = get_market_data_service()
        df = market_data_service.get_stock_data(
            code=stock_code,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        
        # 将DataFrame转换为字典列表，并映射字段名以兼容前端
        data = []
        if not df.empty:
            # 重命名列以匹配前端期望的字段名
            df_renamed = df.rename(columns={
                'open': 'open_price',
                'close': 'close_price',
                'high': 'high_price',
                'low': 'low_price'
            })
            # 将NaN替换为None以生成有效的JSON
            df_renamed = df_renamed.astype(object).where(df_renamed.notna(), None)
            data = df_renamed.to_dict('records')
        
        return jsonify({
            'success': True,
            'data': data,
            'count': len(data)
        })
        
    except Exception as e:
        logger.error(f"获取日线数据失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@stock_bp.route('/<string:stock_code>/latest', methods=['GET'])
def get_stock_latest_data(stock_code):
    """
    获取股票最新数据
    
    Args:
        stock_code: 股票代码
        
    Returns:
        最新数据
    """
    try:
        market_data_service = get_market_data_service()
        data = market_data_service.get_latest_data(stock_code)
        
        if data:
            return jsonify({
                'success': True,
                'data': data
            })
        else:
            return jsonify({
                'success': False,
                'error': '没有数据'
            }), 404
            
    except Exception as e:
        logger.error(f"获取最新数据失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@stock_bp.route('/update', methods=['POST'])
def update_stock_list():
    """
    更新股票列表
    
    Returns:
        更新结果
    """
    try:
        stock_service = get_stock_service()
        result = stock_service.update_stock_list()
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': {
                    'added': result['new_count'],
                    'updated': result['update_count']
                },
                'message': '股票列表更新成功'
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', '更新失败')
            }), 500
            
    except Exception as e:
        logger.error(f"更新股票列表失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@stock_bp.route('/market-data/update', methods=['POST'])
def update_market_data():
    """
    更新行情数据
    
    Body参数:
        days: 更新最近N天的数据（默认5）
        
    Returns:
        更新结果
    """
    try:
        data = request.get_json() or {}
        days = int(data.get('days', 5))
        
        market_data_service = get_market_data_service()
        result = market_data_service.incremental_update(days=days)
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': {
                    'updated_count': result['updated_count']
                },
                'message': '行情数据更新成功'
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', '更新失败')
            }), 500
            
    except Exception as e:
        logger.error(f"更新行情数据失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@stock_bp.route('/search', methods=['GET'])
def search_stocks():
    """
    搜索股票
    
    Query参数:
        q: 搜索关键词（股票代码或名称）
        limit: 返回记录数（默认20）
        
    Returns:
        搜索结果
    """
    try:
        keyword = request.args.get('q', '')
        limit = int(request.args.get('limit', 20))
        
        if not keyword:
            return jsonify({
                'success': False,
                'error': '请提供搜索关键词'
            }), 400
        
        stock_service = get_stock_service()
        stocks = stock_service.search_stocks(keyword, limit=limit)
        
        return jsonify({
            'success': True,
            'data': stocks,
            'count': len(stocks)
        })
        
    except Exception as e:
        logger.error(f"搜索股票失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@stock_bp.route('/list/import', methods=['POST'])
def import_stock_list():
    """
    导入全量股票列表（replace模式）
    如果数据库中已存在股票列表，将用新数据完全替换
    
    Returns:
        导入结果
    """
    try:
        stock_service = get_stock_service()
        result = stock_service.fetch_and_save_stock_list()
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': {
                    'total': result['total'],
                    'success_count': result['success_count'],
                    'fail_count': result['fail_count'],
                    'duration': result['duration']
                },
                'message': '股票列表导入成功'
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('message', '导入失败')
            }), 500
            
    except Exception as e:
        logger.error(f"导入股票列表失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@stock_bp.route('/stats', methods=['GET'])
def get_stock_stats():
    """
    获取股票统计信息
    
    Returns:
        统计信息
    """
    try:
        stock_service = get_stock_service()
        market_data_service = get_market_data_service()
        
        # 获取股票数量统计
        total_stocks = stock_service.count_stocks()
        sh_stocks = stock_service.count_stocks(market='SH')
        sz_stocks = stock_service.count_stocks(market='SZ')
        bj_stocks = stock_service.count_stocks(market='BJ')
        
        # 获取行情数据统计
        data_stats = market_data_service.get_data_stats()
        
        return jsonify({
            'success': True,
            'data': {
                'stocks': {
                    'total': total_stocks,
                    'sh': sh_stocks,
                    'sz': sz_stocks,
                    'bj': bj_stocks
                },
                'market_data': data_stats
            }
        })
        
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
