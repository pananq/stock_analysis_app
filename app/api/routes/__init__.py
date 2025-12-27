"""API路由模块"""
from .strategy_routes import strategy_bp
from .stock_routes import stock_bp
from .system_routes import system_bp
from .data_routes import data_bp

__all__ = [
    'strategy_bp',
    'stock_bp',
    'system_bp',
    'data_bp'
]
