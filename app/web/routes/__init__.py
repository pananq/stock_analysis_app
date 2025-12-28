"""Web路由模块"""
from .dashboard import dashboard_bp
from .strategy import strategy_bp
from .stock import stock_bp
from .system import system_bp
from .data import data_bp
from .auth import auth_bp

__all__ = [
    'dashboard_bp',
    'strategy_bp',
    'stock_bp',
    'system_bp',
    'data_bp',
    'auth_bp'
]
