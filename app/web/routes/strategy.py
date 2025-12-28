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


@strategy_bp.route('/')
def index():
    """策略列表页面"""
    try:
        # 获取策略列表
        response = requests.get(f"{API_BASE_URL}/strategies", timeout=5)
        if response.status_code == 200:
            data = response.json()
            strategies = data.get('data', [])
            stats = data.get('stats', {})
        else:
            strategies = []
            stats = {}
        
        # 获取策略执行记录（从scheduler logs中筛选策略相关的记录）
        try:
            executions_response = requests.get(f"{API_BASE_URL}/system/scheduler/logs?limit=20&offset=0", timeout=5)
            
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
    if request.method == 'POST':
        try:
            # 获取表单数据
            # 处理空字符串，避免转换错误
            min_change = request.form.get('min_change', '0').strip()
            max_change = request.form.get('max_change', '10').strip()
            days = request.form.get('days', '20').strip()
            ma_period = request.form.get('ma_period', '20').strip()
            
            # 构造API期望的数据格式（扁平化，使用Service期望的字段名）
            strategy_data = {
                'name': request.form.get('name'),
                'description': request.form.get('description', ''),
                'rise_threshold': float(min_change) if min_change else 0.0,
                'observation_days': int(days) if days else 20,
                'ma_period': int(ma_period) if ma_period else 20,
                'enabled': request.form.get('enabled') == 'on'
            }
            
            # 验证数据
            if not strategy_data['name']:
                return render_template('strategies/form.html',
                                     strategy=None,
                                     error='策略名称不能为空')
            
            # 创建策略
            response = requests.post(
                f"{API_BASE_URL}/strategies",
                json=strategy_data,
                timeout=5
            )
            
            if response.status_code == 201:
                flash('策略创建成功', 'success')
                return redirect(url_for('strategy.index'))
            else:
                error = response.json().get('error', '创建失败')
                return render_template('strategies/form.html',
                                     strategy=None,
                                     error=error)
        
        except Exception as e:
            logger.error(f"创建策略失败: {e}")
            return render_template('strategies/form.html',
                                 strategy=None,
                                 error=str(e))
    
    return render_template('strategies/form.html', strategy=None)


@strategy_bp.route('/<int:strategy_id>/edit', methods=['GET', 'POST'])
def edit(strategy_id):
    """编辑策略页面"""
    if request.method == 'POST':
        try:
            # 获取表单数据
            # 处理空字符串，避免转换错误
            min_change = request.form.get('min_change', '0').strip()
            max_change = request.form.get('max_change', '10').strip()
            days = request.form.get('days', '20').strip()
            ma_period = request.form.get('ma_period', '20').strip()
            
            # 构造API期望的数据格式（扁平化，使用Service期望的字段名）
            strategy_data = {
                'name': request.form.get('name'),
                'description': request.form.get('description', ''),
                'rise_threshold': float(min_change) if min_change else 0.0,
                'observation_days': int(days) if days else 20,
                'ma_period': int(ma_period) if ma_period else 20,
                'enabled': request.form.get('enabled') == 'on'
            }
            
            # 更新策略
            response = requests.put(
                f"{API_BASE_URL}/strategies/{strategy_id}",
                json=strategy_data,
                timeout=5
            )
            
            if response.status_code == 200:
                flash('策略更新成功', 'success')
                return redirect(url_for('strategy.index'))
            else:
                error = response.json().get('error', '更新失败')
                return render_template('strategies/form.html',
                                     strategy=strategy_data,
                                     strategy_id=strategy_id,
                                     error=error)
        
        except Exception as e:
            logger.error(f"更新策略失败: {e}")
            return render_template('strategies/form.html',
                                 strategy=None,
                                 strategy_id=strategy_id,
                                 error=str(e))
    
    # GET请求：获取策略详情
    try:
        response = requests.get(f"{API_BASE_URL}/strategies/{strategy_id}", timeout=5)
        if response.status_code == 200:
            strategy = response.json().get('data', {})
            
            # 转换数据结构：将API返回的字段名转换为模板期望的字段名
            if 'config' in strategy:
                config = strategy['config']
                strategy['config'] = {
                    'min_change': config.get('rise_threshold', 0),
                    'max_change': 10.0,  # 默认值，数据库中没有存储此字段
                    'days': config.get('observation_days', 20),
                    'ma_period': config.get('ma_period', 20)
                }
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
    try:
        response = requests.post(
            f"{API_BASE_URL}/strategies/{strategy_id}/execute",
            timeout=60  # 策略执行可能需要较长时间
        )
        
        if response.status_code == 200:
            data = response.json()
            flash(f"策略执行完成，共找到 {data.get('data', {}).get('count', 0)} 只股票", 'success')
        else:
            error = response.json().get('error', '执行失败')
            flash(error, 'danger')
    
    except Exception as e:
        logger.error(f"执行策略失败: {e}")
        flash(f"执行失败: {e}", 'danger')
    
    return redirect(url_for('strategy.index'))


@strategy_bp.route('/<int:strategy_id>/delete', methods=['POST'])
def delete(strategy_id):
    """删除策略"""
    try:
        response = requests.delete(
            f"{API_BASE_URL}/strategies/{strategy_id}",
            timeout=5
        )
        
        if response.status_code == 200:
            flash('策略删除成功', 'success')
        else:
            error = response.json().get('error', '删除失败')
            flash(error, 'danger')
    
    except Exception as e:
        logger.error(f"删除策略失败: {e}")
        flash(f"删除失败: {e}", 'danger')
    
    return redirect(url_for('strategy.index'))


@strategy_bp.route('/<int:strategy_id>')
def detail(strategy_id):
    """策略详情页面"""
    try:
        # 获取策略详情
        strategy_response = requests.get(f"{API_BASE_URL}/strategies/{strategy_id}", timeout=5)
        if strategy_response.status_code == 200:
            strategy = strategy_response.json().get('data', {})
            
            # 转换数据结构：将API返回的字段名转换为模板期望的字段名
            if 'config' in strategy:
                config = strategy['config']
                strategy['config'] = {
                    'min_change': config.get('rise_threshold', 0),
                    'max_change': 10.0,  # 默认值，数据库中没有存储此字段
                    'days': config.get('observation_days', 20),
                    'ma_period': config.get('ma_period', 20)
                }
        else:
            return redirect(url_for('strategy.index'))
        
        # 获取最近的执行结果
        results_response = requests.get(
            f"{API_BASE_URL}/strategies/{strategy_id}/results?limit=10",
            timeout=5
        )
        if results_response.status_code == 200:
            results = results_response.json().get('data', [])
        else:
            results = []
        
        return render_template('strategies/detail.html',
                             strategy=strategy,
                             results=results)
    
    except Exception as e:
        logger.error(f"获取策略详情失败: {e}")
        return redirect(url_for('strategy.index'))
