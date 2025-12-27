"""
股票查询路由

提供股票列表、详情和行情查询功能
"""

from flask import Blueprint, render_template, request
import requests
from app.utils import get_logger, get_config

logger = get_logger(__name__)

stock_bp = Blueprint('stock', __name__)

# API基础URL
config = get_config()
API_BASE_URL = f"http://localhost:{config.get('api', {}).get('port', 5000)}/api"


@stock_bp.route('/')
def index():
    """股票列表页面"""
    try:
        # 获取查询参数
        params = {}
        keyword = None
        market = None
        
        # 将前端参数转换为API期望的参数
        code = request.args.get('code')
        name = request.args.get('name')
        
        # 如果有代码或名称，构建关键词搜索
        if code or name:
            keyword = f"{code or ''} {name or ''}".strip()
        
        # 转换市场类型参数
        market_type = request.args.get('market')
        if market_type:
            market_type_map = {
                '沪市': 'SH',
                '深市': 'SZ',
                '北交所': 'BJ'
            }
            market = market_type_map.get(market_type)
        
        # 构建API参数
        if keyword:
            params['keyword'] = keyword
        if market:
            params['market'] = market
        
        # 默认获取前100只股票
        params['limit'] = 100
        
        # 获取股票列表
        response = requests.get(f"{API_BASE_URL}/stocks", params=params, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            stocks = data.get('data', [])
            total = data.get('pagination', {}).get('total', len(stocks))
        else:
            stocks = []
            total = 0
        
        return render_template('stocks/index.html',
                             stocks=stocks,
                             total=total,
                             params=request.args)
    
    except Exception as e:
        logger.error(f"加载股票列表失败: {e}")
        return render_template('stocks/index.html',
                             stocks=[],
                             total=0,
                             error=str(e))


@stock_bp.route('/<string:stock_code>')
def detail(stock_code):
    """股票详情页面"""
    try:
        # 获取股票基本信息
        response = requests.get(f"{API_BASE_URL}/stocks/{stock_code}", timeout=5)
        if response.status_code == 200:
            stock = response.json().get('data', {})
        else:
            return render_template('error.html',
                                 error_code=404,
                                 error_message='股票不存在')
        
        # 获取历史行情数据（最近3个月，约60个交易日）
        history_response = requests.get(
            f"{API_BASE_URL}/stocks/{stock_code}/history",
            params={'limit': 60},
            timeout=5
        )
        if history_response.status_code == 200:
            history_data = history_response.json().get('data', [])
        else:
            history_data = []
        
        return render_template('stocks/detail.html',
                             stock=stock,
                             history_data=history_data)
    
    except Exception as e:
        logger.error(f"加载股票详情失败: {e}")
        return render_template('stocks/detail.html',
                             stock={},
                             history_data=[],
                             error=str(e))
