"""
数据管理路由

提供数据导入、更新和管理功能
"""

from flask import Blueprint, render_template, request
import requests
from app.utils import get_logger, get_config

logger = get_logger(__name__)

data_bp = Blueprint('data', __name__)

# API基础URL
config = get_config()
API_BASE_URL = f"http://localhost:{config.get('api', {}).get('port', 5000)}/api"


@data_bp.route('/')
def index():
    """数据管理页面"""
    try:
        # 获取数据更新状态
        response = requests.get(f"{API_BASE_URL}/data/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            status = data.get('data', {})
        else:
            status = {}
        
        # 检查数据源配置
        datasource_config = {
            'akshare': True,  # Akshare 总是可用的（开源）
            'tushare': False,
            'current_datasource': config.get('datasource', {}).get('type', 'akshare')
        }
        
        # 检查 Tushare 是否已配置
        tushare_token = config.get('datasource.tushare.token') or config.get('datasource.tushare_token')
        datasource_config['tushare'] = bool(tushare_token)
        
        return render_template('data/index.html', status=status, datasource=datasource_config)
    
    except Exception as e:
        logger.error(f"加载数据管理页面失败: {e}")
        return render_template('data/index.html', status={}, error=str(e), datasource={'akshare': True, 'tushare': False})


@data_bp.route('/import', methods=['POST'])
def import_data():
    """触发全量数据导入"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/data/import",
            json=request.get_json() or {},
            timeout=10
        )
        
        if response.status_code == 200:
            return {'success': True, 'message': '数据导入任务已启动'}
        else:
            error = response.json().get('error', '导入失败')
            return {'success': False, 'error': error}
    
    except Exception as e:
        logger.error(f"触发数据导入失败: {e}")
        return {'success': False, 'error': str(e)}


@data_bp.route('/update', methods=['POST'])
def update_data():
    """触发增量数据更新"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/data/update",
            json=request.get_json() or {},
            timeout=10
        )
        
        if response.status_code == 200:
            return {'success': True, 'message': '数据更新任务已启动'}
        else:
            error = response.json().get('error', '更新失败')
            return {'success': False, 'error': error}
    
    except Exception as e:
        logger.error(f"触发数据更新失败: {e}")
        return {'success': False, 'error': str(e)}
