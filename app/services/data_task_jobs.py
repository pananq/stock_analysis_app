"""手工数据任务的统一执行和持久化日志。"""

from datetime import datetime

from app.services.market_identity import SUPPORTED_MARKETS


def _market_summary(result):
    stats = result.get('market_stats') or {}
    return '；'.join(
        (
            f"{market}: 成功{stats.get(market, {}).get('success', 0)}/"
            f"失败{stats.get(market, {}).get('failed', 0)}/"
            f"跳过{stats.get(market, {}).get('skipped', 0)}/"
            f"记录{stats.get(market, {}).get('records', 0)}"
        )
        for market in SUPPORTED_MARKETS
    )


def _failure_message(result, fallback):
    errors = result.get('market_errors') or {}
    if errors:
        return '；'.join(
            f"{market}: {error}" for market, error in errors.items()
        )
    return result.get('message') or result.get('error') or fallback


def _run_logged(job_type, job_name, operation, success_message):
    from app.scheduler import get_task_scheduler

    scheduler = get_task_scheduler()
    started_at = datetime.now()
    job_log_id = scheduler._log_job_start(job_type, job_name)
    try:
        result = operation(job_log_id)
        duration = (datetime.now() - started_at).total_seconds()
        if result.get('success'):
            message = success_message(result)
            if result.get('market_errors'):
                message += (
                    "；未更新范围: "
                    + _failure_message(result, '部分范围未更新')
                )
            scheduler._log_job_success(
                job_type,
                duration,
                message,
                job_log_id,
            )
        else:
            scheduler._log_job_error(
                job_type,
                duration,
                _failure_message(result, f'{job_name}失败'),
                job_log_id,
            )
        if job_log_id:
            result = dict(result)
            result['job_log_id'] = job_log_id
        return result
    except Exception as exc:
        duration = (datetime.now() - started_at).total_seconds()
        scheduler._log_job_error(
            job_type,
            duration,
            str(exc),
            job_log_id,
        )
        raise


def execute_stock_list_import(progress_callback=None, stop_event=None, **_):
    from app.services import get_stock_service

    if stop_event and stop_event.is_set():
        return {'success': False, 'message': '任务已取消', 'cancelled': True}
    return _run_logged(
        'stock_list_import',
        '证券目录导入',
        lambda _job_log_id: get_stock_service().fetch_and_save_stock_list(),
        lambda result: (
            f"总数: {result.get('total', 0)}；"
            f"成功: {result.get('success_count', 0)}；"
            f"失败: {result.get('fail_count', 0)}；"
            f"市场: {result.get('markets', {})}"
        ),
    )


def execute_stock_list_update(progress_callback=None, stop_event=None, **_):
    from app.services import get_stock_service

    if stop_event and stop_event.is_set():
        return {'success': False, 'message': '任务已取消', 'cancelled': True}
    return _run_logged(
        'stock_list_update',
        '证券目录更新',
        lambda _job_log_id: get_stock_service().update_stock_list(),
        lambda result: (
            f"总数: {result.get('total', 0)}；"
            f"新增: {result.get('new_count', 0)}；"
            f"更新: {result.get('update_count', 0)}；"
            f"市场: {result.get('markets', {})}"
        ),
    )


def execute_full_import(progress_callback=None, **kwargs):
    from app.services import get_market_data_service
    from app.scheduler import get_task_scheduler

    scheduler = get_task_scheduler()

    def operation(job_log_id):
        def wrapped_progress(progress, message, **extra):
            if progress_callback:
                progress_callback(progress, message)
            if job_log_id and extra.get('stock_code'):
                scheduler.log_task_detail(
                    job_log_id=job_log_id,
                    task_type='data_import',
                    detail_type=(
                        'stock_import_success'
                        if extra.get('success')
                        else 'stock_import_failed'
                    ),
                    stock_code=extra.get('stock_code'),
                    stock_name=extra.get('stock_name'),
                    detail_data={
                        'records': extra.get('records', 0),
                        'start_date': extra.get('start_date'),
                        'end_date': extra.get('end_date'),
                        'market': extra.get('market'),
                        'security_type': extra.get('security_type'),
                        'error': extra.get('error'),
                    },
                )

        return get_market_data_service().import_all_history(
            start_date=kwargs.get('start_date'),
            end_date=kwargs.get('end_date'),
            limit=kwargs.get('limit'),
            skip=kwargs.get('skip', 0),
            markets=kwargs.get('markets', SUPPORTED_MARKETS),
            progress_callback=wrapped_progress,
            stop_event=kwargs.get('stop_event'),
        )

    return _run_logged(
        'data_import',
        '全量数据导入',
        operation,
        lambda result: (
            f"成功: {result.get('success_count', 0)}；"
            f"失败: {result.get('fail_count', 0)}；"
            f"总记录: {result.get('total_records', 0)}；"
            f"{_market_summary(result)}"
        ),
    )


def execute_recent_update(progress_callback=None, **kwargs):
    from app.services import get_market_data_service
    from app.scheduler import get_task_scheduler

    scheduler = get_task_scheduler()

    def operation(job_log_id):
        def wrapped_progress(progress, message, **extra):
            if progress_callback:
                progress_callback(progress, message)
            if job_log_id and extra.get('stock_code'):
                scheduler.log_task_detail(
                    job_log_id=job_log_id,
                    task_type='data_update',
                    detail_type=(
                        'stock_update_success'
                        if extra.get('success')
                        else 'stock_update_failed'
                    ),
                    stock_code=extra.get('stock_code'),
                    stock_name=extra.get('stock_name'),
                    detail_data={
                        'records': extra.get('records', 0),
                        'start_date': extra.get('start_date'),
                        'end_date': extra.get('end_date'),
                        'market': extra.get('market'),
                        'security_type': extra.get('security_type'),
                        'error': extra.get('error'),
                    },
                )

        return get_market_data_service().update_recent_data(
            days=kwargs.get('days', 5),
            only_existing=False,
            markets=kwargs.get('markets', SUPPORTED_MARKETS),
            progress_callback=wrapped_progress,
            stop_event=kwargs.get('stop_event'),
        )

    return _run_logged(
        'data_update',
        '行情数据更新',
        operation,
        lambda result: (
            f"成功: {result.get('success_count', 0)}；"
            f"失败: {result.get('fail_count', 0)}；"
            f"总记录: {result.get('total_records', 0)}；"
            f"{_market_summary(result)}"
        ),
    )
