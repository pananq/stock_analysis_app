"""
Flask Web应用创建和配置

提供Web界面，包括：
1. 仪表板
2. 策略管理
3. 股票查询
4. 数据管理
5. 系统设置
"""

from flask import Flask, render_template, request
from app.utils import get_config, get_logger

logger = get_logger(__name__)


def create_web_app(config=None):
    """
    创建Flask Web应用
    
    Args:
        config: 配置字典（可选）
        
    Returns:
        Flask应用实例
    """
    app = Flask(__name__,
                template_folder='../templates',
                static_folder='../static')
    
    # 加载配置
    if config is None:
        config = get_config()
    
    # 配置Flask
    app.config['JSON_AS_ASCII'] = False
    app.config['SECRET_KEY'] = config.get('web', {}).get('secret_key', 'dev-secret-key')
    
    # 注册Web路由蓝图
    from app.web.routes import (
        dashboard_bp,
        strategy_bp,
        stock_bp,
        data_bp,
        system_bp
    )
    
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(strategy_bp, url_prefix='/strategies')
    app.register_blueprint(stock_bp, url_prefix='/stocks')
    app.register_blueprint(data_bp, url_prefix='/data')
    app.register_blueprint(system_bp, url_prefix='/system')
    
    logger.info("Web路由注册完成")
    
    # 注册API路由蓝图
    from app.api.routes import (
        strategy_bp as api_strategy_bp,
        stock_bp as api_stock_bp,
        system_bp as api_system_bp,
        data_bp as api_data_bp
    )
    
    app.register_blueprint(api_strategy_bp, url_prefix='/api/strategies', name='api_strategy')
    app.register_blueprint(api_stock_bp, url_prefix='/api/stocks', name='api_stock')
    app.register_blueprint(api_system_bp, url_prefix='/api/system', name='api_system')
    app.register_blueprint(api_data_bp, url_prefix='/api/data', name='api_data')
    
    logger.info("API路由注册完成")
    
    # 注册错误处理器
    register_error_handlers(app)
    
    # 注册模板过滤器
    register_template_filters(app)
    
    logger.info("Flask Web应用创建完成")
    
    return app


def register_error_handlers(app):
    """注册错误处理器"""
    
    @app.errorhandler(404)
    def not_found(error):
        """404错误处理"""
        return render_template('error.html',
                             error_code=404,
                             error_message='页面不存在'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """500错误处理"""
        logger.error(f"Internal error: {error}")
        return render_template('error.html',
                             error_code=500,
                             error_message='服务器内部错误'), 500


def register_template_filters(app):
    """注册模板过滤器"""
    
    @app.template_filter('datetime')
    def format_datetime(value, format='%Y-%m-%d %H:%M:%S'):
        """格式化日期时间"""
        if value is None:
            return ''
        # 如果是字符串，尝试解析
        if isinstance(value, str):
            try:
                from datetime import datetime
                # 处理带逗号的时间格式
                value = value.replace(',', '')
                # 只保留日期时间部分，去掉毫秒
                if '.' in value:
                    value = value.split('.')[0]
                dt = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
                return dt.strftime(format)
            except:
                return value
        # 如果是datetime对象，直接格式化
        try:
            return value.strftime(format)
        except:
            return value
    
    @app.template_filter('number')
    def format_number(value, decimals=2):
        """格式化数字"""
        if value is None:
            return '-'
        try:
            return f'{float(value):.{decimals}f}'
        except:
            return value
    
    @app.template_filter('percent')
    def format_percent(value, decimals=2):
        """格式化百分比"""
        if value is None:
            return '-'
        try:
            return f'{float(value):.{decimals}f}%'
        except:
            return value
    
    @app.template_filter('large_number')
    def format_large_number(value):
        """格式化大数字"""
        if value is None:
            return '-'
        try:
            num = float(value)
            if num >= 100000000:
                return f'{num/100000000:.2f}亿'
            elif num >= 10000:
                return f'{num/10000:.2f}万'
            else:
                return str(int(num))
        except:
            return value
    
    @app.template_filter('formatPctChange')
    def format_pct_change(value):
        """格式化涨跌幅（带颜色）"""
        if value is None:
            return '-'
        try:
            pct = float(value)
            formatted = f'{pct:.2f}%'
            if pct > 0:
                return f'<span class="text-rise">+{formatted}</span>'
            elif pct < 0:
                return f'<span class="text-fall">{formatted}</span>'
            else:
                return formatted
        except:
            return value
