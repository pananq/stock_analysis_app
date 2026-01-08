"""
数据管理API路由

提供数据导入、更新和任务管理功能
"""

from flask import Blueprint, request, jsonify
from app.services import get_market_data_service
from app.task_manager import get_task_manager
from app.models.database_factory import get_database
from app.services.market_data_service import get_market_data_service
from app.utils import get_logger, get_config

logger = get_logger(__name__)

data_bp = Blueprint('data', __name__)


def _execute_full_import(progress_callback=None, **kwargs):
    """执行全量导入的包装函数"""
    from app.scheduler import get_task_scheduler
    
    scheduler = get_task_scheduler()
    job_log_id = scheduler._log_job_start('data_import', '全量数据导入')
    
    # 创建包装的进度回调函数，用于记录详细结果
    def wrapped_progress_callback(progress, message, **extra_data):
        # 调用原始的进度回调
        if progress_callback:
            progress_callback(progress, message)
        
        # 记录详细结果
        if job_log_id and extra_data.get('stock_code'):
            detail_type = 'stock_import_success' if extra_data.get('success') else 'stock_import_failed'
            scheduler.log_task_detail(
                job_log_id=job_log_id,
                task_type='data_import',
                detail_type=detail_type,
                stock_code=extra_data.get('stock_code'),
                stock_name=extra_data.get('stock_name'),
                detail_data={
                    'records': extra_data.get('records', 0),
                    'start_date': extra_data.get('start_date'),
                    'end_date': extra_data.get('end_date'),
                    'error': extra_data.get('error')
                }
            )
    
    try:
        service = get_market_data_service()
        result = service.import_all_history(
            progress_callback=wrapped_progress_callback,
            stop_event=kwargs.get('stop_event')
        )
        
        # 记录任务完成
        if result.get('success'):
            message = f"成功: {result.get('success_count', 0)}, 失败: {result.get('fail_count', 0)}, 总记录: {result.get('total_records', 0)}"
            scheduler._log_job_success('data_import', 0, message)
        else:
            scheduler._log_job_error('data_import', 0, result.get('message', '导入失败'))
        
        return result
    except Exception as e:
        scheduler._log_job_error('data_import', 0, str(e))
        raise


def _execute_incremental_update(progress_callback=None, **kwargs):
    """执行增量更新的包装函数"""
    from app.scheduler import get_task_scheduler
    
    scheduler = get_task_scheduler()
    job_log_id = scheduler._log_job_start('data_update', '增量数据更新')
    
    # 创建包装的进度回调函数，用于记录详细结果
    def wrapped_progress_callback(progress, message, **extra_data):
        # 调用原始的进度回调
        if progress_callback:
            progress_callback(progress, message)
        
        # 记录详细结果
        if job_log_id and extra_data.get('stock_code'):
            detail_type = 'stock_update_success' if extra_data.get('success') else 'stock_update_failed'
            scheduler.log_task_detail(
                job_log_id=job_log_id,
                task_type='data_update',
                detail_type=detail_type,
                stock_code=extra_data.get('stock_code'),
                stock_name=extra_data.get('stock_name'),
                detail_data={
                    'records': extra_data.get('records', 0),
                    'start_date': extra_data.get('start_date'),
                    'end_date': extra_data.get('end_date'),
                    'error': extra_data.get('error')
                }
            )
    
    try:
        service = get_market_data_service()
        result = service.update_recent_data(
            progress_callback=wrapped_progress_callback,
            stop_event=kwargs.get('stop_event')
        )
        
        # 记录任务完成
        if result.get('success'):
            message = f"成功: {result.get('success_count', 0)}, 失败: {result.get('fail_count', 0)}, 总记录: {result.get('total_records', 0)}"
            scheduler._log_job_success('data_update', 0, message)
        else:
            scheduler._log_job_error('data_update', 0, result.get('message', '更新失败'))
        
        return result
    except Exception as e:
        scheduler._log_job_error('data_update', 0, str(e))
        raise


@data_bp.route('/import', methods=['POST'])
def start_full_import():
    """
    启动全量数据导入任务（后台执行）
    
    Request Body（可选）:
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
        limit: 限制导入的股票数量（用于测试）
        skip: 跳过前N只股票
    
    Returns:
        {
            'success': True,
            'task_id': '任务ID',
            'message': '导入任务已启动'
        }
    """
    try:
        # 检查是否已有运行中的导入任务
        task_manager = get_task_manager()
        running_tasks = task_manager.list_tasks(status='running')
        
        if running_tasks:
            running_task_names = [task['task_name'] for task in running_tasks if '导入' in task['task_name']]
            if running_task_names:
                logger.warning(f"已有运行中的导入任务: {running_task_names}")
                return jsonify({
                    'success': False,
                    'error': f'已有运行中的导入任务: {running_task_names[0]}。请等待当前任务完成或取消后再启动新任务。'
                }), 400
        
        data = request.get_json() or {}
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        limit = data.get('limit')
        skip = data.get('skip', 0)
        
        # 创建后台任务
        task_id = task_manager.create_task(
            task_name='全量数据导入',
            func=_execute_full_import,
            auto_start=True
        )
        
        logger.info(f"启动全量导入任务: {task_id}")
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': '全量导入任务已启动，请在后台执行'
        })
        
    except Exception as e:
        logger.error(f"启动全量导入失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@data_bp.route('/update', methods=['POST'])
def start_incremental_update():
    """
    启动增量数据更新任务（后台执行）
    
    Request Body（可选）:
        days: 更新最近N天的数据（默认5）
        only_existing: 是否只更新已有数据的股票（默认true）
    
    Returns:
        {
            'success': True,
            'task_id': '任务ID',
            'message': '更新任务已启动'
        }
    """
    try:
        # 检查是否已有运行中的导入任务
        task_manager = get_task_manager()
        running_tasks = task_manager.list_tasks(status='running')
        
        if running_tasks:
            running_task_names = [task['task_name'] for task in running_tasks if '导入' in task['task_name'] or '更新' in task['task_name']]
            if running_task_names:
                logger.warning(f"已有运行中的数据任务: {running_task_names}")
                return jsonify({
                    'success': False,
                    'error': f'已有运行中的数据任务: {running_task_names[0]}。请等待当前任务完成或取消后再启动新任务。'
                }), 400
        
        data = request.get_json() or {}
        days = data.get('days', 5)
        only_existing = data.get('only_existing', True)
        
        # 创建后台任务
        task_id = task_manager.create_task(
            task_name=f'增量数据更新（最近{days}天）',
            func=_execute_incremental_update,
            auto_start=True
        )
        
        logger.info(f"启动增量更新任务: {task_id}")
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': '增量更新任务已启动，请在后台执行'
        })
        
    except Exception as e:
        logger.error(f"启动增量更新失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@data_bp.route('/tasks/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """
    获取任务状态
    
    Args:
        task_id: 任务ID
    
    Returns:
        {
            'success': True,
            'data': {
                'task_id': '任务ID',
                'task_name': '任务名称',
                'status': 'pending|running|completed|failed',
                'progress': 0-100,
                'message': '任务消息',
                'created_at': '创建时间',
                'started_at': '开始时间',
                'completed_at': '完成时间',
                'error': '错误信息（如果有）',
                'is_running': true/false
            }
        }
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


@data_bp.route('/tasks', methods=['GET'])
def list_tasks():
    """
    获取任务列表
    
    Query参数:
        status: 状态过滤（可选：pending|running|completed|failed）
        limit: 返回记录数（默认10）
    
    Returns:
        {
            'success': True,
            'data': [任务列表],
            'count': 任务数量
        }
    """
    try:
        status = request.args.get('status')
        limit = int(request.args.get('limit', 10))
        
        task_manager = get_task_manager()
        tasks = task_manager.list_tasks(status=status)
        
        # 按创建时间倒序，取前limit个
        tasks = sorted(tasks, key=lambda x: x['created_at'], reverse=True)[:limit]
        
        return jsonify({
            'success': True,
            'data': tasks,
            'count': len(tasks)
        })
        
    except Exception as e:
        logger.error(f"获取任务列表失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@data_bp.route('/tasks/<task_id>/cancel', methods=['POST'])
def cancel_task(task_id):
    """
    取消任务
    
    Args:
        task_id: 任务ID
    
    Returns:
        {
            'success': True,
            'message': '任务已请求取消'
        }
    """
    try:
        task_manager = get_task_manager()
        success = task_manager.cancel_task(task_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': '任务已请求取消'
            })
        else:
            return jsonify({
                'success': False,
                'error': '任务不存在或无法取消'
            }), 404
            
    except Exception as e:
        logger.error(f"取消任务失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@data_bp.route('/status', methods=['GET'])
def get_data_status():
    """
    获取数据状态
    
    Returns:
        {
            'success': True,
            'data': {
                'total_stocks': 股票总数,
                'total_records': 行情记录总数,
                'earliest_date': 最早日期,
                'latest_date': 最新日期,
                'record_count_millions': 记录数（万）
            }
        }
    """
    try:
        market_data_service = get_market_data_service()
        
        # 使用MySQL查询行情数据统计
        stats = market_data_service.get_data_statistics()
        
        return jsonify({
            'success': True,
            'data': {
                'total_stocks': stats.get('stock_count', 0),
                'total_records': stats.get('total_records', 0),
                'earliest_date': stats.get('min_date'),
                'latest_date': stats.get('max_date'),
                'record_count_millions': round(stats.get('total_records', 0) / 10000, 1)
            }
        })
        
    except Exception as e:
        logger.error(f"获取数据状态失败: {e}")
        return jsonify({
            'success': True,
            'data': {
                'total_stocks': 0,
                'total_records': 0,
                'earliest_date': None,
                'latest_date': None,
                'record_count_millions': 0
            },
            'error': str(e)
        })


@data_bp.route('/job-logs/<int:job_log_id>/details', methods=['GET'])
def get_job_details(job_log_id):
    """
    获取任务执行的详细结果
    
    Args:
        job_log_id: 任务日志ID
        
    Query参数:
        limit: 返回记录数（默认1000）
        offset: 偏移量（默认0）
        detail_type: 详细类型过滤（可选）
    
    Returns:
        {
            'success': True,
            'data': {
                'job_log': 任务日志信息,
                'details': 详细结果列表,
                'summary': 统计摘要
            }
        }
    """
    try:
        from app.scheduler import get_task_scheduler
        
        limit = int(request.args.get('limit', 1000))
        offset = int(request.args.get('offset', 0))
        detail_type = request.args.get('detail_type')
        
        scheduler = get_task_scheduler()
        
        # 获取任务日志信息
        job_log = scheduler.db.execute_query(
            "SELECT * FROM job_logs WHERE id = %s",
            (job_log_id,)
        )
        
        if not job_log:
            return jsonify({
                'success': False,
                'error': '任务日志不存在'
            }), 404
        
        # 将datetime对象转换为字符串
        job_log_data = job_log[0]
        if job_log_data.get('started_at'):
            from datetime import datetime
            if isinstance(job_log_data['started_at'], datetime):
                job_log_data['started_at'] = job_log_data['started_at'].strftime('%Y-%m-%d %H:%M:%S')
        if job_log_data.get('completed_at'):
            from datetime import datetime
            if isinstance(job_log_data['completed_at'], datetime):
                job_log_data['completed_at'] = job_log_data['completed_at'].strftime('%Y-%m-%d %H:%M:%S')
        
        # 获取详细结果
        if detail_type:
            details = scheduler.db.execute_query(
                """
                SELECT * FROM task_execution_details
                WHERE job_log_id = %s AND detail_type = %s
                ORDER BY created_at
                LIMIT %s OFFSET %s
                """,
                (job_log_id, detail_type, limit, offset)
            )
        else:
            details = scheduler.get_task_details(job_log_id, limit, offset)

        # 统计摘要
        summary_result = scheduler.db.execute_query(
            """
            SELECT
                detail_type,
                COUNT(*) as count
            FROM task_execution_details
            WHERE job_log_id = %s
            GROUP BY detail_type
            """,
            (job_log_id,)
        )
        
        summary = {row['detail_type']: row['count'] for row in summary_result}
        
        return jsonify({
            'success': True,
            'data': {
                'job_log': job_log_data,
                'details': details,
                'summary': summary,
                'pagination': {
                    'limit': limit,
                    'offset': offset,
                    'total': sum(summary.values())
                }
            }
        })
        
    except Exception as e:
        logger.error(f"获取任务详细结果失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
