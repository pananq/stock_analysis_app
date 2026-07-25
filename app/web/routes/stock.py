"""
股票查询路由

提供股票列表、详情和行情查询功能
"""

from flask import Blueprint, render_template, request, redirect
import requests
from app.utils import get_logger, get_config

logger = get_logger(__name__)

stock_bp = Blueprint('stock', __name__)

# API基础URL
config = get_config()
API_BASE_URL = f"http://localhost:{config.get('api', {}).get('port', 5000)}/api"

def get_auth_headers():
    """获取认证头"""
    token = request.cookies.get('auth_token')
    if token:
        return {'Authorization': f'Bearer {token}'}
    return {}

@stock_bp.route('/')
def index():
    """股票列表页面"""
    try:
        headers = get_auth_headers()
        
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
        
        market_type = request.args.get('market')
        if market_type in {'CN', 'HK', 'US'}:
            market = market_type
        security_type = request.args.get('security_type')
        industry = request.args.get('industry')
        
        # 构建API参数
        if keyword:
            params['keyword'] = keyword
        if market:
            params['market'] = market
        if security_type in {'STOCK', 'ETF', 'FUND', 'INDEX'}:
            params['security_type'] = security_type
        if industry:
            params['industry'] = industry.strip()
        
        # 默认获取前100只股票
        params['limit'] = 100
        
        # 获取股票列表
        response = requests.get(f"{API_BASE_URL}/stocks", params=params, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            stocks = data.get('data', [])
            total = data.get('pagination', {}).get('total', len(stocks))
        elif response.status_code == 401:
            return redirect('/login')
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
        headers = get_auth_headers()
        market = request.args.get('market', 'CN')
        security_type = request.args.get('security_type', 'STOCK')
        
        # 获取股票基本信息
        response = requests.get(
            f"{API_BASE_URL}/stocks/{stock_code}",
            params={
                'market': market,
                'security_type': security_type,
            },
            headers=headers,
            timeout=5,
        )
        if response.status_code == 200:
            stock = response.json().get('data', {})
        elif response.status_code == 401:
            return redirect('/login')
        else:
            return render_template('error.html',
                                 error_code=404,
                                 error_message='股票不存在')
        
        # 获取历史行情数据（最近100天）
        history_response = requests.get(
            f"{API_BASE_URL}/stocks/{stock_code}/history",
            params={
                'limit': 100,
                'market': market,
                'security_type': security_type,
            },
            headers=headers,
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
