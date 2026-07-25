"""Web路由模块"""
from .dashboard import dashboard_bp
from .strategy import strategy_bp
from .stock import stock_bp
from .system import system_bp
from .data import data_bp
from .auth import auth_bp
from .watchlist_routes import watchlist_web_bp
from .api_token_routes import api_token_web_bp
from .report_routes import report_web_bp

__all__ = [
    'dashboard_bp',
    'strategy_bp',
    'stock_bp',
    'system_bp',
    'data_bp',
    'auth_bp',
    'watchlist_web_bp',
    'api_token_web_bp',
    'report_web_bp',
]
