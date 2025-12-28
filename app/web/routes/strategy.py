"""
策略管理路由

提供策略的创建、编辑、删除和执行功能
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
import requests
from app.utils import get_logger, get_config

logger = get_logger(__name__)

strategy_bp = Blueprint('strategy', __name__)

# API基础URL
config = get_config()
API_BASE_URL = f"http://localhost:{config.get('api', {}).get('port', 5000)}/api"

def get_auth_headers():
    """获取认证头"""
    token = request.cookies.get('auth_token')
    if token:
        return {'Authorization': f'Bearer {token}'}
    return {}


@strategy_bp.route('/')
def index():
    """策略列表页面"""
    try:
        headers = get_auth_headers()
        # 获取策略列表
        response = requests.get(f"{API_BASE_URL}/strategies", headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            strategies = data.get('data', [])
            stats = data.get('stats', {})
        elif response.status_code == 401:
            return redirect('/login')
        else:
            strategies = []
            stats = {}
        
        # 获取策略执行记录（从scheduler logs中筛选策略相关的记录）
        try:
            # 系统日志接口需要管理员权限，普通用户可能无法访问
            # 这里尝试获取，如果失败则忽略
            executions_response = requests.get(
                f"{API_BASE_URL}/system/scheduler/logs?limit=20&offset=0", 
                headers=headers,
                timeout=5
            )
            
            if executions_response.status_code == 200:
                all_logs = executions_response.json().get('data', [])
                logger.info(f"获取策略执行记录成功，总日志数: {len(all_logs)}")
                
                # 筛选出策略执行相关的记录（job_type包含'strategy'或job_name包含'策略'）
                # 同时转换数据类型，确保duration是浮点数
                strategy_executions = []
                for log in all_logs:
                    if 'strategy' in log.get('job_type', '').lower() or '策略' in log.get('job_name', ''):
                        # 确保duration是浮点数类型
                        if isinstance(log.get('duration'), str):
                            try:
                                log['duration'] = float(log['duration'])
                            except (ValueError, TypeError):
                                log['duration'] = None
                        strategy_executions.append(log)
                
                logger.info(f"筛选后的策略执行记录数: {len(strategy_executions)}")
            else:
                logger.warning(f"获取执行记录失败，状态码: {executions_response.status_code}")
                strategy_executions = []
        except Exception as e:
            logger.error(f"获取策略执行记录异常: {e}")
            strategy_executions = []
        
        return render_template('strategies/index.html',
                             strategies=strategies,
                             stats=stats,
                             executions=strategy_executions)
    
    except Exception as e:
        logger.error(f"加载策略列表失败: {e}")
        return render_template('strategies/index.html',
                             strategies=[],
                             stats={},
                             executions=[],
                             error=str(e))


@strategy_bp.route('/create', methods=['GET', 'POST'])
def create():
    """创建策略页面"""
    # POST请求已改为前端AJAX提交，这里只处理GET渲染
    return render_template('strategies/form.html', strategy=None)


@strategy_bp.route('/<int:strategy_id>/edit', methods=['GET', 'POST'])
def edit(strategy_id):
    """编辑策略页面"""
    # POST请求已改为前端AJAX提交，这里只处理GET渲染
    
    # GET请求：获取策略详情
    try:
        headers = get_auth_headers()
        response = requests.get(f"{API_BASE_URL}/strategies/{strategy_id}", headers=headers, timeout=5)
        if response.status_code == 200:
            strategy = response.json().get('data', {})
            # 不再需要转换 config 字段，前端已适配 API 返回的字段名
        elif response.status_code == 401:
            return redirect('/login')
        else:
            return redirect(url_for('strategy.index'))
        
        return render_template('strategies/form.html',
                             strategy=strategy,
                             strategy_id=strategy_id)
    
    except Exception as e:
        logger.error(f"获取策略详情失败: {e}")
        return redirect(url_for('strategy.index'))


@strategy_bp.route('/<int:strategy_id>/execute', methods=['POST'])
def execute(strategy_id):
    """执行策略"""
    # 已改为前端AJAX调用
    return jsonify({'error': 'Please use API endpoint'}), 400


@strategy_bp.route('/<int:strategy_id>/delete', methods=['POST'])
def delete(strategy_id):
    """删除策略"""
    # 已改为前端AJAX调用
    return jsonify({'error': 'Please use API endpoint'}), 400


@strategy_bp.route('/<int:strategy_id>')
def detail(strategy_id):
    """策略详情页面"""
    try:
        headers = get_auth_headers()
        # 获取策略详情
        strategy_response = requests.get(f"{API_BASE_URL}/strategies/{strategy_id}", headers=headers, timeout=5)
        if strategy_response.status_code == 200:
            strategy = strategy_response.json().get('data', {})
            # 不再需要转换 config 字段
        elif strategy_response.status_code == 401:
            return redirect('/login')
        else:
            return redirect(url_for('strategy.index'))
        
        # 获取最近的执行结果（原始数据）
        results_response = requests.get(
            f"{API_BASE_URL}/strategies/{strategy_id}/results?limit=100",
            headers=headers,
            timeout=5
        )
        
        raw_results = []
        if results_response.status_code == 200:
            raw_results = results_response.json().get('data', [])
        
        # 聚合结果：按 executed_at 分组
        # 注意：strategy_results 表中的 executed_at 是每条记录的插入时间，同一批次可能略有不同（毫秒级），
        # 但通常是同一秒或非常接近。这里假设同一批次的 executed_at 是相同的（由 StrategyExecutor 统一设置）。
        # 实际上 StrategyExecutor._save_results 中使用的是 now = datetime.now()，是在循环外获取的，所以同一批次的时间完全相同。
        
        from collections import defaultdict
        grouped_results = defaultdict(list)
        
        for res in raw_results:
            # 使用时间字符串作为键
            exec_time = res.get('executed_at')
            grouped_results[exec_time].append(res)
            
        # 转换为列表并排序
        results = []
        for exec_time, items in grouped_results.items():
            # 取第一条记录的信息作为汇总信息
            first = items[0]
            results.append({
                'id': first.get('id'), # 使用第一条记录的ID作为标识，虽然不完全准确
                'executed_at': exec_time,
                'stock_count': len(items),
                'duration': 0, # 无法从 strategy_results 获取 duration，除非关联 job_logs
                'status': 'success',
                'stocks': items # 包含该批次的所有股票
            })
            
        # 按时间倒序排序
        results.sort(key=lambda x: x['executed_at'], reverse=True)
        
        return render_template('strategies/detail.html',
                             strategy=strategy,
                             results=results)
    
    except Exception as e:
        logger.error(f"获取策略详情失败: {e}")
        return redirect(url_for('strategy.index'))
