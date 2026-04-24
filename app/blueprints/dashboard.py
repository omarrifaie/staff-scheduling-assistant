from datetime import date, timedelta

from flask import Blueprint, render_template
from flask_login import login_required

from ..models import Assignment, AuditLog, Employee, Shift
from ..scheduler import detect_conflicts


bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')


@bp.route('/')
@login_required
def index():
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    shifts_this_week = Shift.query.filter(
        Shift.date >= week_start, Shift.date <= week_end
    ).count()

    assignments_this_week = (
        Assignment.query.join(Shift)
        .filter(Shift.date >= week_start, Shift.date <= week_end)
        .count()
    )

    stats = {
        'employee_count': Employee.query.count(),
        'shift_count_this_week': shifts_this_week,
        'assignment_count_this_week': assignments_this_week,
        'conflict_count': len(detect_conflicts(week_start, week_end)),
    }

    recent_audit = (
        AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(8).all()
    )

    return render_template(
        'dashboard/index.html',
        stats=stats,
        recent_audit=recent_audit,
        week_start=week_start,
        week_end=week_end,
    )
