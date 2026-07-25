"""
数据管理API路由

提供数据导入、更新和任务管理功能
"""

from flask import Blueprint, request, jsonify
from app.services import get_market_data_service
from app.task_manager import get_task_manager
from app.models.database_factory import get_database
from app.api.validation import parse_int, validate_date_range
from app.api.responses import internal_error_response
from app.services.market_identity import SUPPORTED_MARKETS
from app.services.data_task_coordinator import (
    DataTaskBusyError,
    create_exclusive_background_task,
    get_data_task_coordinator,
)
from app.services.data_task_jobs import (
    execute_full_import as execute_full_import_job,
    execute_recent_update as execute_recent_update_job,
)
from app.utils import get_logger, get_config

logger = get_logger(__name__)

data_bp = Blueprint('data', __name__)


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
        task_manager = get_task_manager()
        data = request.get_json() or {}
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        validate_date_range(start_date, end_date)
        limit = data.get('limit')
        skip = data.get('skip', 0)

        if limit is not None:
            limit = parse_int(limit, 'limit', minimum=1, maximum=100000)
        skip = parse_int(skip, 'skip', 0, minimum=0)
        
        # 创建后台任务
        task_id = create_exclusive_background_task(
            task_manager,
            task_type='data_import',
            task_name='跨市场全量数据导入（CN/HK/US）',
            func=execute_full_import_job,
            kwargs={
                'start_date': start_date,
                'end_date': end_date,
                'limit': limit,
                'skip': skip,
                'markets': list(SUPPORTED_MARKETS),
            },
        )
        
        logger.info(f"启动全量导入任务: {task_id}")
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'markets': list(SUPPORTED_MARKETS),
            'message': '全量导入任务已启动，请在后台执行'
        })
        
    except DataTaskBusyError as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'active_task': e.active_task,
        }), 409
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
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
        only_existing: 必须为false，避免遗漏尚无行情的港美证券
    
    Returns:
        {
            'success': True,
            'task_id': '任务ID',
            'message': '更新任务已启动'
        }
    """
    try:
        task_manager = get_task_manager()
        data = request.get_json() or {}
        days = parse_int(
            data.get('days'), 'days', 5, minimum=1, maximum=365
        )
        only_existing = data.get('only_existing', False)
        if not isinstance(only_existing, bool):
            return jsonify({
                'success': False,
                'error': 'only_existing 必须是布尔值'
            }), 400
        if only_existing:
            return jsonify({
                'success': False,
                'error': (
                    '多市场行情更新不允许 only_existing=true；'
                    '该选项会排除尚无历史行情的港股和美股'
                ),
            }), 400
        
        # 创建后台任务
        task_id = create_exclusive_background_task(
            task_manager,
            task_type='data_update',
            task_name=(
                f'跨市场行情更新（CN/HK/US，最近{days}天）'
            ),
            func=execute_recent_update_job,
            kwargs={
                'days': days,
                'only_existing': False,
                'markets': list(SUPPORTED_MARKETS),
            },
        )
        
        logger.info(f"启动增量更新任务: {task_id}")
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'markets': list(SUPPORTED_MARKETS),
            'message': '增量更新任务已启动，请在后台执行'
        })
        
    except DataTaskBusyError as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'active_task': e.active_task,
        }), 409
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
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
        limit = parse_int(
            request.args.get('limit'), 'limit', 10, minimum=1, maximum=100
        )
        
        task_manager = get_task_manager()
        tasks = task_manager.list_tasks(status=status)
        
        # 按创建时间倒序，取前limit个
        tasks = sorted(tasks, key=lambda x: x['created_at'], reverse=True)[:limit]
        
        return jsonify({
            'success': True,
            'data': tasks,
            'count': len(tasks)
        })
        
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
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
        
        directory_count = stats.get(
            'directory_count',
            stats.get('stock_count', 0),
        )
        market_data_count = stats.get(
            'market_data_security_count',
            stats.get('stock_count', 0),
        )
        return jsonify({
            'success': True,
            'data': {
                'total_stocks': directory_count,
                'directory_count': directory_count,
                'market_data_security_count': market_data_count,
                'directory_by_market': stats.get('directory_by_market', {}),
                'market_data_by_market': stats.get(
                    'market_data_by_market',
                    {},
                ),
                'total_records': stats.get('total_records', 0),
                'earliest_date': stats.get('min_date'),
                'latest_date': stats.get('max_date'),
                'record_count_millions': round(stats.get('total_records', 0) / 10000, 1),
                'current_task': get_data_task_coordinator().current(),
            }
        })
        
    except Exception as e:
        logger.error(f"获取数据状态失败: {e}")
        return internal_error_response()


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
        
        limit = parse_int(
            request.args.get('limit'), 'limit', 1000, minimum=1, maximum=5000
        )
        offset = parse_int(
            request.args.get('offset'), 'offset', 0, minimum=0
        )
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
        
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"获取任务详细结果失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
