"""
系统设置路由

提供系统配置、日志查看等功能
"""

from flask import Blueprint, render_template, request
import requests
from app.utils import get_logger, get_config

logger = get_logger(__name__)

system_bp = Blueprint('system', __name__)

# API基础URL
config = get_config()
API_BASE_URL = f"http://localhost:{config.get('api', {}).get('port', 5000)}/api"


@system_bp.route('/')
def index():
    """系统设置页面"""
    try:
        # 获取可编辑配置
        config_response = requests.get(f"{API_BASE_URL}/system/config", timeout=5)
        if config_response.status_code == 200:
            system_config = config_response.json().get('data', {})
        else:
            system_config = {}
        
        # 获取系统信息（仅展示）
        info_response = requests.get(f"{API_BASE_URL}/system/system-info", timeout=5)
        if info_response.status_code == 200:
            system_info_config = info_response.json().get('data', {})
        else:
            system_info_config = {}
        
        # 获取数据库状态
        db_status_response = requests.get(f"{API_BASE_URL}/system/database-status", timeout=5)
        if db_status_response.status_code == 200:
            database_status = db_status_response.json().get('data', {})
        else:
            database_status = {}
        
        # 获取调度任务列表
        jobs_response = requests.get(f"{API_BASE_URL}/system/scheduler/jobs", timeout=5)
        jobs = jobs_response.json().get('data', []) if jobs_response.status_code == 200 else []
        
        # 获取市场统计信息（用于显示数据范围）
        stats_response = requests.get(f"{API_BASE_URL}/system/stats", timeout=5)
        stats = stats_response.json().get('data', {}) if stats_response.status_code == 200 else {}
        market_stats = stats.get('market_data', {})
        
        return render_template('system/index.html',
                             system_config=system_config,
                             system_info_config=system_info_config,
                             database_status=database_status,
                             jobs=jobs,
                             market_stats=market_stats)
    
    except Exception as e:
        logger.error(f"加载系统设置页面失败: {e}")
        return render_template('system/index.html',
                             system_config={},
                             system_info_config={},
                             database_status={},
                             jobs=[],
                             market_stats={},
                             error=str(e))


@system_bp.route('/logs')
def logs():
    """系统日志页面"""
    try:
        # 获取查询参数
        params = {'limit': 100}
        if request.args.get('level'):
            params['level'] = request.args.get('level')
        if request.args.get('module'):
            params['module'] = request.args.get('module')
        
        # 获取系统日志
        response = requests.get(f"{API_BASE_URL}/system/logs", params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            logs = data.get('data', [])
            total = data.get('total', len(logs))
        else:
            logs = []
            total = 0
        
        return render_template('system/logs.html',
                             logs=logs,
                             total=total,
                             params=request.args)
    
    except Exception as e:
        logger.error(f"加载系统日志页面失败: {e}")
        return render_template('system/logs.html',
                             logs=[],
                             total=0,
                             error=str(e))


@system_bp.route('/tasks')
def tasks():
    """任务执行历史页面"""
    try:
        # 获取任务执行历史
        response = requests.get(f"{API_BASE_URL}/system/scheduler/logs?limit=50", timeout=5)
        if response.status_code == 200:
            data = response.json()
            tasks = data.get('data', [])
            total = data.get('total', len(tasks))
        else:
            tasks = []
            total = 0
        
        return render_template('system/tasks.html',
                             tasks=tasks,
                             total=total)
    
    except Exception as e:
        logger.error(f"加载任务历史页面失败: {e}")
        return render_template('system/tasks.html',
                             tasks=[],
                             total=0,
                             error=str(e))
