"""
关注列表 API 路由
"""
from flask import Blueprint, request, jsonify, g
from app.services.watchlist_service import get_watchlist_service
from app.utils import get_logger

logger = get_logger(__name__)

watchlist_bp = Blueprint('watchlist', __name__)


@watchlist_bp.route('', methods=['GET'])
def get_watchlist():
    """获取当前用户的关注列表"""
    try:
        user_id = g.user['user_id']
        group_name = request.args.get('group')
        tag = request.args.get('tag')

        result = get_watchlist_service().get_watchlist(user_id, group_name=group_name, tag=tag)
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        logger.error(f"获取关注列表失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@watchlist_bp.route('', methods=['POST'])
def add_stock():
    """添加股票到关注列表"""
    try:
        user_id = g.user['user_id']
        data = request.get_json() or {}

        stock_code = data.get('stock_code')
        if not stock_code:
            return jsonify({'success': False, 'error': '缺少 stock_code 参数'}), 400

        result = get_watchlist_service().add_stock(
            user_id=user_id,
            stock_code=stock_code,
            market=data.get('market', 'CN'),
            group_name=data.get('group_name'),
            tags=data.get('tags'),
            notes=data.get('notes')
        )

        if result.get('success'):
            return jsonify(result), 201
        else:
            return jsonify(result), 409  # Conflict if already exists
    except Exception as e:
        logger.error(f"添加关注股票失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@watchlist_bp.route('/<int:watchlist_id>', methods=['PUT'])
def update_stock(watchlist_id):
    """更新关注条目"""
    try:
        user_id = g.user['user_id']
        data = request.get_json() or {}

        result = get_watchlist_service().update_stock(user_id, watchlist_id, **data)

        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 404
    except Exception as e:
        logger.error(f"更新关注条目失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@watchlist_bp.route('/<int:watchlist_id>', methods=['DELETE'])
def remove_stock(watchlist_id):
    """删除关注条目"""
    try:
        user_id = g.user['user_id']
        success = get_watchlist_service().remove_stock(user_id, watchlist_id)

        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': '条目不存在'}), 404
    except Exception as e:
        logger.error(f"删除关注条目失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@watchlist_bp.route('/<string:stock_code>/data', methods=['GET'])
def get_stock_data(stock_code):
    """查询股票历史数据+技术指标"""
    try:
        user_id = g.user['user_id']
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        ma_periods_str = request.args.get('ma_periods', '5,30,60')
        market = request.args.get('market', 'CN')

        try:
            ma_periods = [int(p.strip()) for p in ma_periods_str.split(',') if p.strip()]
        except ValueError:
            return jsonify({'success': False, 'error': 'ma_periods 格式无效'}), 400

        result = get_watchlist_service().get_stock_data_with_indicators(
            stock_code=stock_code,
            start_date=start_date,
            end_date=end_date,
            ma_periods=ma_periods
        )

        return jsonify({
            'success': True,
            'data': {
                'stock_code': stock_code,
                'market': market,
                **result
            }
        })
    except Exception as e:
        logger.error(f"查询股票数据失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
