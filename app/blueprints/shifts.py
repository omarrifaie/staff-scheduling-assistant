from datetime import date as date_type, time

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..audit_helpers import log_action
from ..models import ROLES, Shift, db


bp = Blueprint('shifts', __name__, url_prefix='/shifts')


def _shift_snapshot(shift):
    return (
        f"{shift.date.isoformat()} "
        f"{shift.start_time.strftime('%H:%M')}-{shift.end_time.strftime('%H:%M')} "
        f"role={shift.required_role} min_staff={shift.min_staff} "
        f"notes='{shift.notes or ''}'"
    )


def _parse_shift_form():
    try:
        shift_date = date_type.fromisoformat(request.form['date'])
        start_time = time.fromisoformat(request.form['start_time'])
        end_time = time.fromisoformat(request.form['end_time'])
    except (KeyError, ValueError):
        return None, 'Date, start time, and end time are required in valid formats'

    if end_time <= start_time:
        return None, 'End time must be after start time'

    required_role = (request.form.get('required_role') or '').strip()
    if required_role not in ROLES:
        return None, 'A valid required role is required'

    try:
        min_staff = int(request.form.get('min_staff') or 1)
    except ValueError:
        min_staff = 1
    if min_staff < 1:
        min_staff = 1

    notes = (request.form.get('notes') or '').strip()

    return {
        'date': shift_date,
        'start_time': start_time,
        'end_time': end_time,
        'required_role': required_role,
        'min_staff': min_staff,
        'notes': notes,
    }, None


@bp.route('/')
@login_required
def index():
    shifts = Shift.query.order_by(Shift.date, Shift.start_time).all()
    return render_template('shifts/index.html', shifts=shifts)


@bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    if request.method == 'POST':
        data, error = _parse_shift_form()
        if error:
            flash(error, 'error')
            return redirect(url_for('shifts.new'))

        shift = Shift(**data)
        db.session.add(shift)
        db.session.commit()

        log_action(
            current_user,
            'create',
            'Shift',
            shift.id,
            f"Created shift: {_shift_snapshot(shift)}",
        )
        flash('Shift created', 'success')
        return redirect(url_for('shifts.index'))

    return render_template('shifts/form.html', shift=None, roles=ROLES)


@bp.route('/<int:shift_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(shift_id):
    shift = Shift.query.get_or_404(shift_id)

    if request.method == 'POST':
        data, error = _parse_shift_form()
        if error:
            flash(error, 'error')
            return redirect(url_for('shifts.edit', shift_id=shift_id))

        before = _shift_snapshot(shift)
        for field, value in data.items():
            setattr(shift, field, value)
        db.session.commit()
        after = _shift_snapshot(shift)

        log_action(
            current_user,
            'update',
            'Shift',
            shift.id,
            f"Updated shift. Before: {before} || After: {after}",
        )
        flash('Shift updated', 'success')
        return redirect(url_for('shifts.index'))

    return render_template('shifts/form.html', shift=shift, roles=ROLES)


@bp.route('/<int:shift_id>/delete', methods=['POST'])
@login_required
def delete(shift_id):
    shift = Shift.query.get_or_404(shift_id)
    snapshot = _shift_snapshot(shift)

    db.session.delete(shift)
    db.session.commit()

    log_action(
        current_user,
        'delete',
        'Shift',
        shift_id,
        f"Deleted shift: {snapshot}",
    )
    flash('Shift deleted', 'success')
    return redirect(url_for('shifts.index'))
