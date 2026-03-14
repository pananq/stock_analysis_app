"""API Token 管理 Web 路由"""
from flask import Blueprint, render_template
from app.utils import get_logger

logger = get_logger(__name__)

api_token_web_bp = Blueprint('api_token_web', __name__)

@api_token_web_bp.route('/api-tokens')
def api_tokens():
    """API Token 管理页面"""
    return render_template('api_tokens.html')
