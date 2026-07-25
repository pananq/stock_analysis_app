"""日报页面。"""

from flask import Blueprint, render_template


report_web_bp = Blueprint('report_web', __name__)


@report_web_bp.route('/reports')
def reports():
    return render_template('reports.html')
