"""
API Token 管理路由
"""
from flask import Blueprint, request, jsonify, g
from app.api.responses import internal_error_response
from app.services.api_token_service import get_api_token_service
from app.utils import get_logger

logger = get_logger(__name__)

api_token_bp = Blueprint('api_token', __name__)


@api_token_bp.route('', methods=['GET'])
def list_tokens():
    """列出当前用户的 API Token"""
    try:
        user_id = g.user['user_id']
        tokens = get_api_token_service().list_tokens(user_id)
        return jsonify({'success': True, 'data': tokens})
    except Exception as e:
        logger.error(f"列出 API Token 失败: {e}")
        return internal_error_response()


@api_token_bp.route('', methods=['POST'])
def create_token():
    """创建新的 API Token（返回明文，仅一次）"""
    try:
        user_id = g.user['user_id']
        data = request.get_json() or {}

        name = data.get('name')
        if not name:
            return jsonify({'success': False, 'error': '缺少 name 参数'}), 400

        result = get_api_token_service().create_token(user_id, name)

        if result.get('success'):
            return jsonify(result), 201
        else:
            return jsonify(result), 500
    except Exception as e:
        logger.error(f"创建 API Token 失败: {e}")
        return internal_error_response()


@api_token_bp.route('/<int:token_id>', methods=['DELETE'])
def revoke_token(token_id):
    """撤销 API Token"""
    try:
        user_id = g.user['user_id']
        success = get_api_token_service().revoke_token(user_id, token_id)

        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Token 不存在'}), 404
    except Exception as e:
        logger.error(f"撤销 API Token 失败: {e}")
        return internal_error_response()
