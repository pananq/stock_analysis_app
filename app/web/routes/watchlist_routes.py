"""关注列表 Web 路由"""
from flask import Blueprint, render_template
from app.utils import get_logger

logger = get_logger(__name__)

watchlist_web_bp = Blueprint('watchlist_web', __name__)

@watchlist_web_bp.route('/watchlist')
def watchlist():
    """关注列表页面"""
    return render_template('watchlist.html')
