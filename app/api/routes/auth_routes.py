from flask import Blueprint, request, jsonify, g
from app.services.auth_service import AuthService
from app.utils.logger import get_logger

logger = get_logger(__name__)
auth_bp = Blueprint('auth', __name__)
auth_service = AuthService()

@auth_bp.route('/register', methods=['POST'])
def register():
    """用户注册"""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
        
    username = data.get('username')
    password = data.get('password')
    
    logger.info(f"收到注册请求: username={username}")
    
    if not username or not password:
        logger.warning("注册失败: 用户名或密码为空")
        return jsonify({'error': 'Username and password are required'}), 400
        
    success, message, user_info = auth_service.register(username, password)
    
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
        
    success, message, token, user_info = auth_service.login(username, password)
    
    if success:
        logger.info(f"用户登录成功: username={username}")
        return jsonify({
            'message': message,
            'token': token,
            'user': user_info
        }), 200
    else:
        logger.warning(f"用户登录失败: username={username}, reason={message}")
        return jsonify({'error': message}), 401

@auth_bp.route('/me', methods=['GET'])
def get_current_user():
    """获取当前用户信息"""
    # g.user 由中间件设置
    if not hasattr(g, 'user') or not g.user:
        return jsonify({'error': 'Unauthorized'}), 401
        
    return jsonify({'user': g.user}), 200

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """用户注销"""
    # JWT 是无状态的，客户端只需丢弃 Token 即可
    # 如果需要服务端注销，需要维护一个 Token 黑名单
    return jsonify({'message': 'Logout successful'}), 200
