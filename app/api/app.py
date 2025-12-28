"""
Flask应用创建和配置

提供RESTful API接口，包括：
1. 策略管理API
2. 股票查询API
3. 系统管理API
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime
from app.utils import get_config, get_logger
from app.models.database_factory import get_database
from app.services.market_data_service import get_market_data_service

logger = get_logger(__name__)


def configure_werkzeug_logging():
    """
    配置Werkzeug日志，使用容错处理器避免I/O错误
    Werkzeug是Flask使用的WSGI工具包
    """
    import logging
    from logging.handlers import RotatingFileHandler
    
    # 获取Werkzeug日志记录器
    werkzeug_logger = logging.getLogger('werkzeug')
    
    # 移除所有现有的处理器
    werkzeug_logger.handlers.clear()
    
    # 创建容错的文件处理器
    log_path = './logs/api.log'
    try:
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=10,
            encoding='utf-8'
        )
        
        # 设置容错处理器
        class SafeRotatingFileHandler(RotatingFileHandler):
            def emit(self, record):
                try:
                    super().emit(record)
                except (OSError, IOError):
                    # 静默处理文件写入错误
                    pass
                except Exception:
                    pass
        
        file_handler = SafeRotatingFileHandler(
            log_path,
            maxBytes=10*1024*1024,
            backupCount=10,
            encoding='utf-8'
        )
        
        # 设置格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        werkzeug_logger.addHandler(file_handler)
        werkzeug_logger.setLevel(logging.INFO)
        
        # 禁用Werkzeug的异常传播
        werkzeug_logger.propagate = False
        werkzeug_logger.raiseExceptions = False
        
    except Exception as e:
        # 如果配置失败，只输出到控制台
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        werkzeug_logger.addHandler(console_handler)


def create_app(config=None):
    """
    创建Flask应用
    
    Args:
        config: 配置字典（可选）
        
    Returns:
        Flask应用实例
    """
    app = Flask(__name__)
    
    # 加载配置
    if config is None:
        config = get_config()
    
    # 配置Flask
    app.config['JSON_AS_ASCII'] = False  # 支持中文
    app.config['JSON_SORT_KEYS'] = False  # 不排序键
    
    # 配置CORS（跨域资源共享）
    api_config = config.get('api', {})
    cors_origins = api_config.get('cors_origins', '*')
    CORS(app, origins=cors_origins)
    
    # 配置Werkzeug日志使用容错处理器
    configure_werkzeug_logging()
    
    # 初始化数据库（使用 ORM 模式）
    with app.app_context():
        get_database()  # 使用工厂方法获取数据库（MySQL或SQLite）
        get_market_data_service()  # 初始化MySQL行情数据库
        logger.info("数据库初始化完成")
    
    # 注册蓝图
    from app.api.routes import strategy_bp, stock_bp, system_bp, data_bp
    
    app.register_blueprint(strategy_bp, url_prefix='/api/strategies')
    app.register_blueprint(stock_bp, url_prefix='/api/stocks')
    app.register_blueprint(system_bp, url_prefix='/api/system')
    app.register_blueprint(data_bp, url_prefix='/api/data')
    
    logger.info("API路由注册完成")
    
    # 注册错误处理器
    register_error_handlers(app)
    
    # 注册请求钩子
    register_request_hooks(app)
    
    # 根路径
    @app.route('/')
    def index():
        """API根路径"""
        from datetime import datetime
        return jsonify({
            'name': '股票分析系统API',
            'version': '1.0.0',
            'status': 'running',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'endpoints': {
                'strategies': '/api/strategies',
                'stocks': '/api/stocks',
                'system': '/api/system'
            }
        })
    
    # 健康检查
    @app.route('/health')
    def health():
        """健康检查"""
        try:
            from datetime import datetime

            # 检查数据库连接
            db = get_database()  # 使用工厂方法获取数据库（MySQL或SQLite）
            market_data_service = get_market_data_service()

            db_result = db.execute_query("SELECT 1")

            # 检查MySQL行情数据
            market_db_ok = False
            try:
                stats = market_data_service.get_data_statistics()
                market_db_ok = stats is not None
            except:
                market_db_ok = False

            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'database': {
                    'main': 'ok' if db_result else 'error',
                    'market_data': 'ok' if market_db_ok else 'error'
                }
            })
        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            return jsonify({
                'status': 'unhealthy',
                'error': str(e)
            }), 500
    
    logger.info("Flask应用创建完成")
    
    return app


def register_error_handlers(app):
    """注册错误处理器"""
    
    @app.errorhandler(400)
    def bad_request(error):
        """400错误处理"""
        return jsonify({
            'error': 'Bad Request',
            'message': str(error)
        }), 400
    
    @app.errorhandler(404)
    def not_found(error):
        """404错误处理"""
        return jsonify({
            'error': 'Not Found',
            'message': 'The requested resource was not found'
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """500错误处理"""
        logger.error(f"Internal error: {error}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An internal error occurred'
        }), 500
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        """通用异常处理"""
        logger.error(f"Unhandled exception: {error}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': str(error)
        }), 500


def register_request_hooks(app):
    """注册请求钩子"""
    
    @app.before_request
    def before_request():
        """请求前处理"""
        # 记录请求信息
        logger.debug(f"Request: {request.method} {request.path}")
    
    @app.after_request
    def after_request(response):
        """请求后处理"""
        # 记录响应信息
        logger.debug(f"Response: {response.status_code}")
        return response


if __name__ == '__main__':
    """应用入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='股票分析系统 API 服务')
    parser.add_argument('--host', default='0.0.0.0', help='主机地址')
    parser.add_argument('--port', type=int, default=5000, help='端口号')
    parser.add_argument('--debug', action='store_true', help='调试模式')
    
    args = parser.parse_args()
    
    app = create_app()
    logger.info(f"启动 API 服务: http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug)

