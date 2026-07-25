"""关注列表日报 API。"""

from flask import Blueprint, g, jsonify

from app.api.responses import internal_error_response
from app.services.daily_report_service import (
    get_daily_report_service,
)
from app.utils import get_config, get_logger


logger = get_logger(__name__)
report_bp = Blueprint('reports', __name__)


@report_bp.route('/settings', methods=['GET'])
def report_settings():
    config = get_config()
    targets = get_daily_report_service().get_targets()
    user_id = int(g.user['user_id'])
    return jsonify({
        'success': True,
        'data': {
            'ai_enabled': bool(config.get('ai.enabled', False)),
            'ai_model': config.get('ai.model'),
            'email_enabled': bool(config.get('notifications.email.enabled', False)),
            'schedule_enabled': bool(
                config.get('notifications.daily_report.enabled', False)
            ),
            'schedule_time': config.get('notifications.daily_report.time', '20:00'),
            'target_count': len(targets),
            'can_send': any(
                target['user_id'] == user_id for target in targets
            ),
        },
    })


@report_bp.route('/daily/preview', methods=['POST'])
def preview_daily_report():
    try:
        report = get_daily_report_service().build_report(g.user['user_id'])
        return jsonify({'success': True, 'data': report})
    except ValueError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    except Exception as exc:
        logger.exception("生成关注列表日报失败")
        return internal_error_response()


@report_bp.route('/daily/send', methods=['POST'])
def send_daily_report():
    try:
        result = get_daily_report_service().send_report(g.user['user_id'])
        return jsonify(result)
    except ValueError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    except Exception as exc:
        logger.exception("发送关注列表日报失败")
        return internal_error_response()
