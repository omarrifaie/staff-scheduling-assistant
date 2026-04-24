from datetime import date as date_type, timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..audit_helpers import log_action
from ..models import Assignment, Employee, Shift, db
from ..scheduler import can_assign, detect_conflicts, generate_schedule


bp = Blueprint('schedule', __name__, url_prefix='/schedule')


def _parse_week(week_start_param):
    start = None
    if week_start_param:
        try:
            start = date_type.fromisoformat(week_start_param)
        except ValueError:
            start = None
    if start is None:
        today = date_type.today()
        start = today - timedelta(days=today.weekday())
    end = start + timedelta(days=6)
    return start, end


@bp.route('/')
@login_required
def index():
    start, end = _parse_week(request.args.get('week_start'))

    shifts = (
        Shift.query
        .filter(Shift.date >= start, Shift.date <= end)
        .order_by(Shift.date, Shift.start_time)
        .all()
    )

    by_day = {}
    for offset in range(7):
        by_day[start + timedelta(days=offset)] = []
    for shift in shifts:
        by_day.setdefault(shift.date, []).append(shift)

    conflicts = detect_conflicts(start, end)

    prev_week = start - timedelta(days=7)
    next_week = start + timedelta(days=7)

    employees = Employee.query.order_by(Employee.role, Employee.name).all()

    return render_template(
        'schedule/index.html',
        week_start=start,
        week_end=end,
        by_day=by_day,
        conflicts=conflicts,
        prev_week=prev_week,
        next_week=next_week,
        employees=employees,
    )


@bp.route('/generate', methods=['POST'])
@login_required
def generate():
    start, end = _parse_week(request.form.get('week_start'))
    result = generate_schedule(start, end)

    log_action(
        current_user,
        'generate',
        'Schedule',
        None,
        (
            f"Generated schedule for {start.isoformat()} through {end.isoformat()}: "
            f"{result['assignments_created']} assignments across "
            f"{result['shift_count']} shifts, {len(result['conflicts'])} conflict(s)"
        ),
    )

    if result['conflicts']:
        flash(
            f"Schedule generated with {result['assignments_created']} assignments. "
            f"{len(result['conflicts'])} conflict(s) detected.",
            'warning',
        )
    else:
        flash(
            f"Schedule generated with {result['assignments_created']} assignments. No conflicts.",
            'success',
        )
    return redirect(url_for('schedule.index', week_start=start.isoformat()))


@bp.route('/clear', methods=['POST'])
@login_required
def clear():
    start, end = _parse_week(request.form.get('week_start'))
    shift_ids = [
        s.id for s in Shift.query.filter(Shift.date >= start, Shift.date <= end).all()
    ]
    cleared = 0
    if shift_ids:
        cleared = Assignment.query.filter(
            Assignment.shift_id.in_(shift_ids)
        ).delete(synchronize_session=False)
        db.session.commit()

    log_action(
        current_user,
        'clear',
        'Schedule',
        None,
        f"Cleared {cleared} assignments for {start.isoformat()} through {end.isoformat()}",
    )
    flash(f'Cleared {cleared} assignments for this week', 'success')
    return redirect(url_for('schedule.index', week_start=start.isoformat()))


@bp.route('/assign', methods=['POST'])
@login_required
def assign():
    try:
        shift_id = int(request.form['shift_id'])
        employee_id = int(request.form['employee_id'])
    except (KeyError, ValueError):
        flash('Invalid assignment request', 'error')
        return redirect(url_for('schedule.index'))

    week_start_param = request.form.get('week_start')

    shift = Shift.query.get_or_404(shift_id)
    employee = Employee.query.get_or_404(employee_id)

    existing = Assignment.query.filter_by(
        shift_id=shift_id, employee_id=employee_id
    ).first()
    if existing:
        flash(f'{employee.name} is already assigned to this shift', 'error')
        return redirect(url_for('schedule.index', week_start=week_start_param))

    ok, reason = can_assign(employee, shift)
    if not ok:
        flash(f'Cannot assign {employee.name}: {reason}', 'error')
        return redirect(url_for('schedule.index', week_start=week_start_param))

    assignment = Assignment(shift_id=shift_id, employee_id=employee_id)
    db.session.add(assignment)
    db.session.commit()

    log_action(
        current_user,
        'create',
        'Assignment',
        assignment.id,
        (
            f"Assigned {employee.name} to shift {shift.date.isoformat()} "
            f"{shift.start_time.strftime('%H:%M')}-{shift.end_time.strftime('%H:%M')} "
            f"({shift.required_role})"
        ),
    )
    flash(f'{employee.name} assigned to shift', 'success')
    return redirect(url_for('schedule.index', week_start=week_start_param))


@bp.route('/unassign/<int:assignment_id>', methods=['POST'])
@login_required
def unassign(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)
    week_start_param = request.form.get('week_start')

    description = (
        f"Removed {assignment.employee.name} from shift "
        f"{assignment.shift.date.isoformat()} "
        f"{assignment.shift.start_time.strftime('%H:%M')}-"
        f"{assignment.shift.end_time.strftime('%H:%M')} "
        f"({assignment.shift.required_role})"
    )

    db.session.delete(assignment)
    db.session.commit()

    log_action(
        current_user,
        'delete',
        'Assignment',
        assignment_id,
        description,
    )
    flash('Assignment removed', 'success')
    return redirect(url_for('schedule.index', week_start=week_start_param))
