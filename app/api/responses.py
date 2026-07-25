"""统一 API 错误响应，避免把数据库或上游服务细节暴露给客户端。"""

from flask import jsonify


def internal_error_response():
    return jsonify({
        'success': False,
        'error': '服务器内部错误，请稍后重试',
    }), 500
