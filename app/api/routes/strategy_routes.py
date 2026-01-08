"""
策略管理API路由

提供策略的CRUD操作和执行功能
"""

from flask import Blueprint, request, jsonify, g
from app.services import get_strategy_service, get_strategy_executor
from app.task_manager import get_task_manager
from app.utils import get_logger
from decimal import Decimal

logger = get_logger(__name__)

strategy_bp = Blueprint('strategy', __name__)

def convert_decimal(obj):
    """转换Decimal为float以便JSON序列化"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: convert_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimal(v) for v in obj]
    return obj


@strategy_bp.route('', methods=['GET'])
def list_strategies():
    """
    获取策略列表
    
    Query参数:
        enabled_only: 是否只返回启用的策略（true/false）
        
    Returns:
        策略列表和统计信息
    """
    try:
        enabled_only = request.args.get('enabled_only', 'false').lower() == 'true'
        
        # 获取当前用户
        user = getattr(g, 'user', None)
        user_id = None
        
        if user:
            # 如果不是管理员，只能查看自己的策略
            if user.get('role') != 'admin':
                user_id = user.get('user_id')
            # 如果是管理员，默认查看所有，也可以通过参数筛选特定用户（暂未实现参数筛选）
        
        strategy_service = get_strategy_service()
        strategies = strategy_service.list_strategies(enabled_only=enabled_only, user_id=user_id)
        
        # 计算统计信息
        if enabled_only:
            # 如果只查询启用的策略，需要重新获取所有策略来统计
            all_strategies = strategy_service.list_strategies(enabled_only=False, user_id=user_id)
        else:
            all_strategies = strategies
        
        total = len(all_strategies)
        enabled = sum(1 for s in all_strategies if s.get('enabled'))
        disabled = total - enabled
        
        return jsonify({
            'success': True,
            'data': strategies,
            'count': len(strategies),
            'stats': {
                'total': total,
                'enabled': enabled,
                'disabled': disabled
            }
        })
        
    except Exception as e:
        logger.error(f"获取策略列表失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@strategy_bp.route('/<int:strategy_id>', methods=['GET'])
def get_strategy(strategy_id):
    """
    获取策略详情
    
    Args:
        strategy_id: 策略ID
        
    Returns:
        策略详情
    """
    try:
        # 获取当前用户
        user = getattr(g, 'user', None)
        user_id = None
        if user and user.get('role') != 'admin':
            user_id = user.get('user_id')
            
        strategy_service = get_strategy_service()
        strategy = strategy_service.get_strategy(strategy_id, user_id=user_id)
        
        if strategy:
            return jsonify({
                'success': True,
                'data': strategy
            })
        else:
            return jsonify({
                'success': False,
                'error': '策略不存在或无权访问'
            }), 404
            
    except Exception as e:
        logger.error(f"获取策略详情失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@strategy_bp.route('', methods=['POST'])
def create_strategy():
    """
    创建策略
    
    Body参数:
        name: 策略名称（必填）
        description: 策略描述
        rise_threshold: 涨幅阈值（必填）
        observation_days: 观察天数（必填）
        ma_period: 均线周期（必填）
        enabled: 是否启用（默认true）
        
    Returns:
        创建的策略ID
    """
    try:
        data = request.get_json()
        
        # 获取当前用户
        user = getattr(g, 'user', None)
        if not user:
            return jsonify({'success': False, 'error': '未登录'}), 401
            
        user_id = user.get('user_id')
        
        # 验证必填参数
        required_fields = ['name', 'rise_threshold', 'observation_days', 'ma_period']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'缺少必填参数: {field}'
                }), 400
        
        strategy_service = get_strategy_service()
        
        # 检查策略名称是否已存在（同一用户下）
        existing_strategy = strategy_service.get_strategy_by_name(data['name'], user_id=user_id)
        if existing_strategy:
            return jsonify({
                'success': False,
                'error': '策略名称已存在，请使用其他名称'
            }), 400
        
        strategy_id = strategy_service.create_strategy(
            name=data['name'],
            user_id=user_id,
            description=data.get('description', ''),
            rise_threshold=float(data['rise_threshold']),
            observation_days=int(data['observation_days']),
            ma_period=int(data['ma_period']),
            enabled=data.get('enabled', True)
        )
        
        if strategy_id:
            return jsonify({
                'success': True,
                'data': {
                    'id': strategy_id
                },
                'message': '策略创建成功'
            }), 201
        else:
            return jsonify({
                'success': False,
                'error': '策略创建失败，请检查参数或稍后重试'
            }), 500
            
    except Exception as e:
        logger.error(f"创建策略失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@strategy_bp.route('/<int:strategy_id>', methods=['PUT'])
def update_strategy(strategy_id):
    """
    更新策略
    
    Args:
        strategy_id: 策略ID
        
    Body参数:
        name: 策略名称
        description: 策略描述
        rise_threshold: 涨幅阈值
        observation_days: 观察天数
        ma_period: 均线周期
        enabled: 是否启用
        
    Returns:
        更新结果
    """
    try:
        data = request.get_json()
        
        # 获取当前用户
        user = getattr(g, 'user', None)
        user_id = None
        if user and user.get('role') != 'admin':
            user_id = user.get('user_id')
        
        strategy_service = get_strategy_service()
        success = strategy_service.update_strategy(strategy_id, user_id=user_id, **data)
        
        if success:
            return jsonify({
                'success': True,
                'message': '策略更新成功'
            })
        else:
            return jsonify({
                'success': False,
                'error': '策略更新失败或无权操作'
            }), 500
            
    except Exception as e:
        logger.error(f"更新策略失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@strategy_bp.route('/<int:strategy_id>', methods=['DELETE'])
def delete_strategy(strategy_id):
    """
    删除策略
    
    Args:
        strategy_id: 策略ID
        
    Returns:
        删除结果
    """
    try:
        # 获取当前用户
        user = getattr(g, 'user', None)
        user_id = None
        if user and user.get('role') != 'admin':
            user_id = user.get('user_id')
            
        strategy_service = get_strategy_service()
        success = strategy_service.delete_strategy(strategy_id, user_id=user_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': '策略删除成功'
            })
        else:
            return jsonify({
                'success': False,
                'error': '策略删除失败或无权操作'
            }), 500
            
    except Exception as e:
        logger.error(f"删除策略失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@strategy_bp.route('/<int:strategy_id>/execute', methods=['POST'])
def execute_strategy(strategy_id):
    """
    执行策略（异步任务）
    
    Args:
        strategy_id: 策略ID
        
    Body参数:
        start_date: 开始日期（可选，默认30天前）
        end_date: 结束日期（可选，默认今天）
        
    Returns:
        任务ID
    """
    try:
        data = request.get_json() or {}
        
        # 获取当前用户
        user = getattr(g, 'user', None)
        user_id = None
        if user:
            user_id = user.get('user_id')
            # 如果不是管理员，检查策略权限
            if user.get('role') != 'admin':
                strategy_service = get_strategy_service()
                strategy = strategy_service.get_strategy(strategy_id, user_id=user_id)
                if not strategy:
                    return jsonify({'success': False, 'error': '策略不存在或无权访问'}), 404
        
        from datetime import datetime, timedelta
        from app.scheduler import get_task_scheduler
        
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        # 获取策略信息
        strategy_service = get_strategy_service()
        strategy = strategy_service.get_strategy(strategy_id) # 这里不需要再传 user_id，因为上面已经检查过了，或者管理员可以直接获取
        if not strategy:
            return jsonify({
                'success': False,
                'error': '策略不存在'
            }), 404
        
        strategy_name = strategy.get('name', f'策略#{strategy_id}')
        
        # 创建包装函数，用于记录任务日志
        def execute_with_logging(progress_callback=None, stop_event=None):
            scheduler = get_task_scheduler()
            # 记录 user_id
            job_log_id = scheduler._log_job_start('manual_strategy', f'执行策略: {strategy_name}', user_id=user_id)
            logger.info(f"任务开始记录: job_log_id={job_log_id}")
            
            try:
                strategy_executor = get_strategy_executor()
                result = strategy_executor.execute_strategy(
                    strategy_id=strategy_id,
                    start_date=start_date,
                    end_date=end_date,
                    progress_callback=progress_callback,
                    stop_event=stop_event
                )
                
                logger.info(f"策略执行完成: success={result.get('success')}, job_log_id={job_log_id}, matches_count={len(result.get('matches', []))}")
                
                if result.get('success'):
                    # 记录匹配的股票详情
                    if job_log_id and result.get('matches'):
                        logger.info(f"开始记录{len(result['matches'])}个匹配的股票详情到task_execution_details表")
                        saved_details = 0
                        for match in result['matches']:
                            try:
                                # 转换Decimal类型
                                trigger_date = match.get('trigger_date')
                                if isinstance(trigger_date, datetime):
                                    trigger_date = trigger_date.strftime('%Y-%m-%d')
                                elif isinstance(trigger_date, str):
                                    pass  # 已经是字符串
                                else:
                                    trigger_date = str(trigger_date)
                                
                                detail_data = {
                                    'trigger_date': trigger_date,
                                    'trigger_pct_change': convert_decimal(match.get('trigger_pct_change')),
                                    'observation_days': match.get('observation_days'),
                                    'ma_period': match.get('ma_period'),
                                    'observation_result': convert_decimal(match.get('observation_result'))
                                }
                                
                                scheduler.log_task_detail(
                                    job_log_id=job_log_id,
                                    task_type='strategy_execution',
                                    detail_type='strategy_match',
                                    stock_code=match.get('stock_code'),
                                    stock_name=match.get('stock_name'),
                                    detail_data=detail_data
                                )
                                saved_details += 1
                            except Exception as e:
                                logger.error(f"记录股票详情失败: {match.get('stock_code')}, 错误: {e}")
                                import traceback
                                traceback.print_exc()
                        logger.info(f"成功记录{saved_details}条股票详情")
                    else:
                        logger.warning(f"未记录股票详情: job_log_id={job_log_id}, has_matches={bool(result.get('matches'))}, matches_count={len(result.get('matches', []))}")
                    
                    message = f"成功: {result.get('matched_count', 0)}, 扫描: {result.get('scanned_stocks', 0)}"
                    
                    # 获取任务开始时间
                    job_info = scheduler.db.execute_query(
                        "SELECT started_at FROM job_logs WHERE id = %s",
                        (job_log_id,)
                    )
                    if job_info:
                        started_at = job_info[0]['started_at']
                        # 确保 started_at 是 datetime 类型
                        if isinstance(started_at, str):
                            started_at = datetime.strptime(started_at, '%Y-%m-%d %H:%M:%S')
                        # 如果已经是datetime类型，不需要转换
                        elif isinstance(started_at, datetime):
                            pass
                        else:
                            started_at = datetime.now()
                        duration = (datetime.now() - started_at).total_seconds()
                    else:
                        duration = 0
                    
                    scheduler._log_job_success('manual_strategy', duration, message)
                else:
                    error_msg = result.get('error', '未知错误')
                    scheduler._log_job_error('manual_strategy', 0, error_msg)
                
                return result
            except Exception as e:
                logger.error(f"策略执行异常: {e}")
                import traceback
                traceback.print_exc()
                scheduler._log_job_error('manual_strategy', 0, str(e))
                raise
        
        # 创建异步任务
        task_manager = get_task_manager()
        
        task_id = task_manager.create_task(
            task_name=f'执行策略: {strategy_name}',
            func=execute_with_logging,
            auto_start=True
        )
        
        return jsonify({
            'success': True,
            'data': {
                'task_id': task_id
            },
            'message': '策略执行任务已创建，正在后台执行'
        })
            
    except Exception as e:
        logger.error(f"创建策略执行任务失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@strategy_bp.route('/<int:strategy_id>/results', methods=['GET'])
def get_strategy_results(strategy_id):
    """
    获取策略执行结果
    
    Args:
        strategy_id: 策略ID
        
    Query参数:
        limit: 返回记录数（默认100）
        offset: 偏移量（默认0）
        
    Returns:
        策略执行结果列表
    """
    try:
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        
        strategy_executor = get_strategy_executor()
        results = strategy_executor.get_strategy_results(
            strategy_id=strategy_id,
            limit=limit,
            offset=offset
        )
        
        total = strategy_executor.get_strategy_results_count(strategy_id)
        
        return jsonify({
            'success': True,
            'data': results,
            'pagination': {
                'total': total,
                'limit': limit,
                'offset': offset,
                'has_more': offset + len(results) < total
            }
        })
        
    except Exception as e:
        logger.error(f"获取策略结果失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@strategy_bp.route('/<int:strategy_id>/enable', methods=['POST'])
def enable_strategy(strategy_id):
    """
    启用策略
    
    Args:
        strategy_id: 策略ID
        
    Returns:
        操作结果
    """
    try:
        # 获取当前用户
        user = getattr(g, 'user', None)
        user_id = None
        if user and user.get('role') != 'admin':
            user_id = user.get('user_id')
            
        strategy_service = get_strategy_service()
        success = strategy_service.update_strategy(strategy_id, user_id=user_id, enabled=True)
        
        if success:
            return jsonify({
                'success': True,
                'message': '策略已启用'
            })
        else:
            return jsonify({
                'success': False,
                'error': '启用策略失败或无权操作'
            }), 500
            
    except Exception as e:
        logger.error(f"启用策略失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@strategy_bp.route('/<int:strategy_id>/disable', methods=['POST'])
def disable_strategy(strategy_id):
    """
    禁用策略
    
    Args:
        strategy_id: 策略ID
        
    Returns:
        操作结果
    """
    try:
        # 获取当前用户
        user = getattr(g, 'user', None)
        user_id = None
        if user and user.get('role') != 'admin':
            user_id = user.get('user_id')
            
        strategy_service = get_strategy_service()
        success = strategy_service.update_strategy(strategy_id, user_id=user_id, enabled=False)
        
        if success:
            return jsonify({
                'success': True,
                'message': '策略已禁用'
            })
        else:
            return jsonify({
                'success': False,
                'error': '禁用策略失败或无权操作'
            }), 500
            
    except Exception as e:
        logger.error(f"禁用策略失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@strategy_bp.route('/tasks/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """
    获取策略执行任务状态
    
    Args:
        task_id: 任务ID
        
    Returns:
        任务状态信息
    """
    try:
        task_manager = get_task_manager()
        task = task_manager.get_task(task_id)
        
        if task:
            return jsonify({
                'success': True,
                'data': task
            })
        else:
            return jsonify({
                'success': False,
                'error': '任务不存在'
            }), 404
            
    except Exception as e:
        logger.error(f"获取任务状态失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
