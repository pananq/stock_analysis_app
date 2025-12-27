"""
系统管理API路由

提供系统管理和监控功能
"""

from flask import Blueprint, request, jsonify
from app.scheduler import get_task_scheduler
from app.utils import get_logger, get_config

logger = get_logger(__name__)

system_bp = Blueprint('system', __name__)


@system_bp.route('/info', methods=['GET'])
def get_system_info():
    """
    获取系统信息
    
    Returns:
        系统信息
    """
    try:
        config = get_config()
        
        return jsonify({
            'success': True,
            'data': {
                'name': '股票分析系统',
                'version': '1.0.0',
                'datasource': config.get('datasource', {}).get('type', 'unknown'),
                'database': {
                    'duckdb': config.get('database', {}).get('duckdb_path', '')
                }
            }
        })
        
    except Exception as e:
        logger.error(f"获取系统信息失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@system_bp.route('/scheduler/jobs', methods=['GET'])
def get_scheduler_jobs():
    """
    获取调度任务列表
    
    Returns:
        任务列表
    """
    try:
        scheduler = get_task_scheduler()
        jobs = scheduler.get_jobs()
        
        return jsonify({
            'success': True,
            'data': jobs,
            'count': len(jobs)
        })
        
    except Exception as e:
        logger.error(f"获取任务列表失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@system_bp.route('/scheduler/jobs/<string:job_id>/run', methods=['POST'])
def run_scheduler_job(job_id):
    """
    立即执行调度任务
    
    Args:
        job_id: 任务ID
        
    Returns:
        执行结果
    """
    try:
        scheduler = get_task_scheduler()
        success = scheduler.run_job_now(job_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': '任务已触发执行'
            })
        else:
            return jsonify({
                'success': False,
                'error': '任务不存在或触发失败'
            }), 404
            
    except Exception as e:
        logger.error(f"执行任务失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@system_bp.route('/logs', methods=['GET'])
def get_system_logs():
    """
    获取系统日志
    
    Query参数:
        limit: 返回记录数（默认100）
        level: 日志级别过滤（可选）
        module: 模块过滤（可选）
        
    Returns:
        日志列表
    """
    try:
        import re
        from datetime import datetime
        
        limit = int(request.args.get('limit', 100))
        level_filter = request.args.get('level', '').upper()
        module_filter = request.args.get('module', '').lower()
        
        config = get_config()
        log_file = config.get('logging', {}).get('file_path', './logs/app.log')
        
        logs = []
        
        # 读取日志文件
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            # 解析日志行
            # 格式: 2025-12-27 00:00:00,000 - module.name - LEVEL - message
            log_pattern = re.compile(
                r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - ([^ ]+) - (\w+) - (.+)'
            )
            
            for line in reversed(lines):  # 从最新的开始
                line = line.strip()
                if not line:
                    continue
                    
                match = log_pattern.match(line)
                if match:
                    timestamp_str, module, level, message = match.groups()
                    
                    # 应用过滤器
                    if level_filter and level != level_filter:
                        continue
                    if module_filter and module_filter not in module.lower():
                        continue
                    
                    # 解析时间戳
                    try:
                        from datetime import timezone
                        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f')
                        created_at = timestamp.replace(tzinfo=timezone.utc).strftime('%Y-%m-%d %H:%M:%S GMT')
                    except:
                        created_at = timestamp_str
                    
                    logs.append({
                        'created_at': created_at,
                        'module': module,
                        'level': level,
                        'message': message
                    })
                    
                    if len(logs) >= limit:
                        break
                        
        except FileNotFoundError:
            logger.warning(f"日志文件不存在: {log_file}")
        except Exception as e:
            logger.error(f"读取日志文件失败: {e}")
        
        return jsonify({
            'success': True,
            'data': logs,
            'total': len(logs)
        })
        
    except Exception as e:
        logger.error(f"获取系统日志失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@system_bp.route('/scheduler/logs', methods=['GET'])
def get_scheduler_logs():
    """
    获取调度任务日志
    
    Query参数:
        limit: 返回记录数（默认100）
        offset: 偏移量（默认0）
        
    Returns:
        任务日志列表
    """
    try:
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        
        scheduler = get_task_scheduler()
        logs = scheduler.get_job_logs(limit=limit, offset=offset)
        total = scheduler.get_job_logs_count()
        
        return jsonify({
            'success': True,
            'data': logs,
            'pagination': {
                'total': total,
                'limit': limit,
                'offset': offset,
                'has_more': offset + len(logs) < total
            }
        })
        
    except Exception as e:
        logger.error(f"获取任务日志失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@system_bp.route('/scheduler/start', methods=['POST'])
def start_scheduler():
    """
    启动调度器
    
    Returns:
        操作结果
    """
    try:
        scheduler = get_task_scheduler()
        scheduler.start()
        
        return jsonify({
            'success': True,
            'message': '调度器已启动'
        })
        
    except Exception as e:
        logger.error(f"启动调度器失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@system_bp.route('/scheduler/stop', methods=['POST'])
def stop_scheduler():
    """
    停止调度器
    
    Returns:
        操作结果
    """
    try:
        scheduler = get_task_scheduler()
        scheduler.shutdown(wait=False)
        
        return jsonify({
            'success': True,
            'message': '调度器已停止'
        })
        
    except Exception as e:
        logger.error(f"停止调度器失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@system_bp.route('/config', methods=['GET'])
def get_config_info():
    """
    获取配置信息（可编辑部分）
    
    Returns:
        配置信息
    """
    try:
        config = get_config()
        
        # 返回可编辑的配置（不含敏感信息和系统级配置）
        editable_config = {
            'app_mode': {
                'mode': config.get('app_mode', {}).get('mode', 'production'),
                'development_stock_limit': config.get('app_mode', {}).get('development_stock_limit', 100)
            },
            'datasource': {
                'type': config.get('datasource', {}).get('type', 'akshare')
            },
            'api_rate_limit': {
                'min_delay': config.get('api_rate_limit', {}).get('min_delay', 1.5),
                'max_delay': config.get('api_rate_limit', {}).get('max_delay', 2.0),
                'max_retries': config.get('api_rate_limit', {}).get('max_retries', 3),
                'retry_delay_increment': config.get('api_rate_limit', {}).get('retry_delay_increment', 1.0)
            },
            'scheduler': {
                'enable_auto_update': config.get('scheduler', {}).get('enable_auto_update', True),
                'stock_list_update_time': config.get('scheduler', {}).get('stock_list_update_time', '18:00'),
                'market_data_update_time': config.get('scheduler', {}).get('market_data_update_time', '18:30'),
                'timezone': config.get('scheduler', {}).get('timezone', 'Asia/Shanghai')
            },
            'data_management': {
                'data_retention_years': config.get('data_management', {}).get('data_retention_years', 5),
                'enable_auto_backup': config.get('data_management', {}).get('enable_auto_backup', True),
                'backup_retention_days': config.get('data_management', {}).get('backup_retention_days', 30)
            },
            'strategy_defaults': {
                'rise_threshold': config.get('strategy_defaults', {}).get('rise_threshold', 8.0),
                'observation_days': config.get('strategy_defaults', {}).get('observation_days', 3),
                'ma_period': config.get('strategy_defaults', {}).get('ma_period', 5)
            }
        }
        
        return jsonify({
            'success': True,
            'data': editable_config
        })
        
    except Exception as e:
        logger.error(f"获取配置信息失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@system_bp.route('/config', methods=['PUT'])
def update_config_info():
    """
    更新配置信息
    
    Request Body:
        要更新的配置项
        
    Returns:
        更新结果
    """
    try:
        import yaml
        import os
        
        # 获取请求体
        updates = request.get_json()
        if not updates:
            return jsonify({
                'success': False,
                'error': '请提供要更新的配置'
            }), 400
        
        config = get_config()
        
        # 读取配置文件路径
        config_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'config.yaml')
        
        # 读取当前配置
        with open(config_file, 'r', encoding='utf-8') as f:
            current_config = yaml.safe_load(f)
        
        # 更新配置
        for section, section_updates in updates.items():
            if section in current_config:
                if isinstance(section_updates, dict):
                    for key, value in section_updates.items():
                        current_config[section][key] = value
                else:
                    current_config[section] = section_updates
        
        # 写入配置文件
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.safe_dump(current_config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        
        logger.info(f"配置已更新: {list(updates.keys())}")
        
        return jsonify({
            'success': True,
            'message': '配置已更新，重启后生效'
        })
        
    except FileNotFoundError:
        logger.error("配置文件不存在")
        return jsonify({
            'success': False,
            'error': '配置文件不存在'
        }), 404
    except Exception as e:
        logger.error(f"更新配置失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@system_bp.route('/database-status', methods=['GET'])
def get_database_status():
    """
    获取数据库健康状态
    
    Returns:
        数据库状态信息
    """
    try:
        from app.models.database_factory import get_database
        from app.models import get_duckdb
        
        db = get_database()
        duckdb = get_duckdb()
        
        # 检查主数据库
        main_db_status = {
            'type': db.type if hasattr(db, 'type') else 'unknown',
            'status': 'unknown',
            'error': None
        }
        
        try:
            result = db.execute_query("SELECT 1")
            if result:
                main_db_status['status'] = 'healthy'
            else:
                main_db_status['status'] = 'error'
        except Exception as e:
            main_db_status['status'] = 'error'
            main_db_status['error'] = str(e)
        
        # 检查DuckDB
        duckdb_status = {
            'type': 'duckdb',
            'status': 'unknown',
            'error': None
        }
        
        try:
            result = duckdb.execute_query("SELECT 1")
            if result:
                duckdb_status['status'] = 'healthy'
            else:
                duckdb_status['status'] = 'error'
        except Exception as e:
            duckdb_status['status'] = 'error'
            duckdb_status['error'] = str(e)
        
        return jsonify({
            'success': True,
            'data': {
                'main_database': main_db_status,
                'duckdb': duckdb_status
            }
        })
        
    except Exception as e:
        logger.error(f"获取数据库状态失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@system_bp.route('/system-info', methods=['GET'])
def get_system_info_config():
    """
    获取系统级配置信息（仅用于显示）
    
    Returns:
        系统级配置（端口、调试模式等）
    """
    try:
        config = get_config()
        
        system_info = {
            'api': {
                'port': config.get('api', {}).get('port', 5000),
                'host': config.get('api', {}).get('host', '0.0.0.0')
            },
            'web': {
                'port': config.get('web', {}).get('port', 8000),
                'host': config.get('web', {}).get('host', '0.0.0.0'),
                'debug': config.get('web', {}).get('debug', False)
            },
            'logging': {
                'level': config.get('logging', {}).get('level', 'INFO'),
                'file_path': config.get('logging', {}).get('file_path', './logs/app.log')
            }
        }
        
        return jsonify({
            'success': True,
            'data': system_info
        })
        
    except Exception as e:
        logger.error(f"获取系统配置信息失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@system_bp.route('/health', methods=['GET'])
def health_check():
    """
    健康检查
    
    Returns:
        健康状态
    """
    try:
        from app.models.database_factory import get_database
        from app.models import get_duckdb
        
        db = get_database()  # 使用工厂方法获取数据库（MySQL或SQLite）
        duckdb = get_duckdb()
        
        # 检查数据库连接
        main_db_ok = False
        duckdb_ok = False
        
        try:
            result = db.execute_query("SELECT 1")
            main_db_ok = bool(result)
        except:
            pass
        
        try:
            result = duckdb.execute_query("SELECT 1")
            duckdb_ok = bool(result)
        except:
            pass
        
        # 检查调度器状态
        scheduler_ok = False
        try:
            scheduler = get_task_scheduler()
            scheduler_ok = scheduler.scheduler.running
        except:
            pass
        
        all_ok = main_db_ok and duckdb_ok
        
        return jsonify({
            'success': True,
            'data': {
                'status': 'healthy' if all_ok else 'degraded',
                'components': {
                    'database': 'ok' if main_db_ok else 'error',
                    'duckdb': 'ok' if duckdb_ok else 'error',
                    'scheduler': 'running' if scheduler_ok else 'stopped'
                }
            }
        }), 200 if all_ok else 503
        
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@system_bp.route('/stats', methods=['GET'])
def get_system_stats():
    """
    获取系统统计信息
    
    Returns:
        统计信息
    """
    try:
        from app.models.database_factory import get_database
        from app.models import get_duckdb
        from app.services import get_stock_service, get_strategy_service
        
        db = get_database()  # 使用工厂方法获取数据库（MySQL或SQLite）
        stock_service = get_stock_service()
        strategy_service = get_strategy_service()
        
        # 股票数量
        total_stocks = stock_service.count_stocks()
        
        # 策略数量
        strategies = strategy_service.list_strategies()
        enabled_strategies = [s for s in strategies if s.get('enabled')]
        
        # 行情数据统计（带重试机制）
        market_stats = {
            'stock_count': 0,
            'record_count': 0,
            'earliest_date': None,
            'latest_date': None
        }
        
        max_retries = 3
        retry_delay = 0.5
        
        for attempt in range(max_retries):
            try:
                duckdb = get_duckdb()
                result = duckdb.execute_query("""
                    SELECT 
                        COUNT(DISTINCT code) as stock_count,
                        COUNT(*) as record_count,
                        MIN(trade_date) as earliest_date,
                        MAX(trade_date) as latest_date
                    FROM daily_market
                """)
                
                if result:
                    market_stats = result[0]
                break  # 成功则退出重试循环
                
            except Exception as e:
                logger.warning(f"获取DuckDB统计信息失败（尝试 {attempt + 1}/{max_retries}）: {e}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(retry_delay)
                    retry_delay *= 2  # 指数退避
                else:
                    logger.error(f"获取DuckDB统计信息失败，已达到最大重试次数: {e}")
        
        # 任务日志统计
        scheduler = get_task_scheduler()
        job_log_count = scheduler.get_job_logs_count()
        
        return jsonify({
            'success': True,
            'data': {
                'stocks': {
                    'total': total_stocks
                },
                'strategies': {
                    'total': len(strategies),
                    'enabled': len(enabled_strategies)
                },
                'market_data': {
                    'stock_count': market_stats.get('stock_count', 0),
                    'record_count': market_stats.get('record_count', 0),
                    'earliest_date': market_stats.get('earliest_date'),
                    'latest_date': market_stats.get('latest_date')
                },
                'job_logs': {
                    'total': job_log_count
                }
            }
        })
        
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
