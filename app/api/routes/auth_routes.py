from flask import Blueprint, request, jsonify, g
from app.services.auth_service import AuthService
from app.utils.logger import get_logger

logger = get_logger(__name__)
auth_bp = Blueprint('auth', __name__)


def get_auth_service():
    """延迟创建服务，避免导入路由模块时就连接数据库。"""
    return AuthService()

@auth_bp.route('/register', methods=['POST'])
def register():
    """用户注册"""
    from app.utils import get_config

    if not get_config().get('auth.enable_registration', False):
        return jsonify({'error': 'Registration is disabled'}), 403
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
        
    username = data.get('username')
    password = data.get('password')
    
    logger.info(f"收到注册请求: username={username}")
    
    if not username or not password:
        logger.warning("注册失败: 用户名或密码为空")
        return jsonify({'error': 'Username and password are required'}), 400
        
    success, message, user_info = get_auth_service().register(username, password)
    
    if success:
        logger.info(f"用户注册成功: username={username}")
        return jsonify({
            'success': True,
            'message': message,
            'user': user_info
        }), 201
    else:
        logger.warning(f"用户注册失败: username={username}, reason={message}")
        return jsonify({'error': message}), 400

@auth_bp.route('/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.get_json()
    if not data:
        logger.warning("登录失败: 未提供数据")
        return jsonify({'error': 'No data provided'}), 400
        
    username = data.get('username')
    password = data.get('password')
    
    logger.info(f"收到登录请求: username={username}")
    
    if not username or not password:
        logger.warning("登录失败: 用户名或密码为空")
        return jsonify({'error': 'Username and password are required'}), 400
        
    success, message, token, user_info = get_auth_service().login(username, password)
    
    if success:
        from app.utils import get_config

        logger.info(f"用户登录成功: username={username}")
        payload = {
            'success': True,
            'message': message,
            'user': user_info
        }
        # 浏览器同源登录只依赖 HttpOnly Cookie，不把 JWT 暴露给 JavaScript。
        # 外部 API 客户端保持原有响应，可获取 Bearer Token。
        if request.args.get('session_only') not in {'1', 'true'}:
            payload['token'] = token
        response = jsonify(payload)
        config = get_config()
        max_age = int(config.get('auth.token_expire_hours', 24)) * 3600
        response.set_cookie(
            'auth_token',
            token,
            max_age=max_age,
            httponly=True,
            secure=bool(config.get('web.ssl_enabled', False)),
            samesite='Lax',
            path='/',
        )
        return response, 200
    else:
        logger.warning(f"用户登录失败: username={username}, reason={message}")
        return jsonify({'error': message}), 401

@auth_bp.route('/me', methods=['GET'])
def get_current_user():
    """获取当前用户信息"""
    # g.user 由中间件设置
    if not hasattr(g, 'user') or not g.user:
        return jsonify({'error': 'Unauthorized'}), 401
        
    user = get_auth_service().get_user_by_id(g.user['user_id'])
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    return jsonify({'user': user}), 200


@auth_bp.route('/profile', methods=['GET'])
def get_profile():
    """获取当前用户个人资料。"""
    user = get_auth_service().get_user_by_id(g.user['user_id'])
    if not user:
        return jsonify({'error': '用户不存在'}), 404
    return jsonify({'success': True, 'user': user}), 200


@auth_bp.route('/profile', methods=['PUT'])
def update_profile():
    """更新当前用户个人资料。"""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'error': 'No data provided'}), 400
    if (
        'daily_report_enabled' in data
        and not isinstance(data['daily_report_enabled'], bool)
    ):
        return jsonify({'error': '邮件日报开关必须为布尔值'}), 400

    current = get_auth_service().get_user_by_id(g.user['user_id'])
    if not current:
        return jsonify({'error': '用户不存在'}), 404

    success, message, user = get_auth_service().update_profile(
        g.user['user_id'],
        data.get('nickname', current.get('nickname')),
        data.get('email', current.get('email')),
        data.get(
            'daily_report_enabled',
            current.get('daily_report_enabled', False),
        ),
    )
    if not success:
        status = 404 if message == '用户不存在' else 400
        return jsonify({'error': message}), status
    return jsonify({
        'success': True,
        'message': message,
        'user': user,
    }), 200

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """用户注销"""
    response = jsonify({'message': 'Logout successful'})
    response.delete_cookie('auth_token', path='/', samesite='Lax')
    return response, 200
