"""
仪表板路由

显示系统概览和统计信息
"""

from flask import Blueprint, render_template
import requests
from app.utils import get_logger, get_config

logger = get_logger(__name__)

dashboard_bp = Blueprint('dashboard', __name__)

# API基础URL
config = get_config()
API_BASE_URL = f"http://localhost:{config.get('api', {}).get('port', 5000)}/api"


@dashboard_bp.route('/')
def index():
    """仪表板首页"""
    try:
        # 获取系统统计信息
        stats_response = requests.get(f"{API_BASE_URL}/system/stats", timeout=5)
        stats = stats_response.json().get('data', {}) if stats_response.status_code == 200 else {}
        
        # 获取数据源状态
        info_response = requests.get(f"{API_BASE_URL}/system/info", timeout=5)
        system_info = info_response.json().get('data', {}) if info_response.status_code == 200 else {}
        
        # 获取最近的任务日志
        logs_response = requests.get(f"{API_BASE_URL}/system/scheduler/logs?limit=5", timeout=5)
        recent_logs = logs_response.json().get('data', []) if logs_response.status_code == 200 else []
        
        return render_template('dashboard.html',
                             stats=stats,
                             system_info=system_info,
                             recent_logs=recent_logs)
    
    except Exception as e:
        logger.error(f"加载仪表板失败: {e}")
        return render_template('dashboard.html',
                             stats={},
                             system_info={},
                             recent_logs=[],
                             error=str(e))
