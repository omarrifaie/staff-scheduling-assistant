from datetime import time

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..audit_helpers import log_action
from ..models import (
    Availability,
    DAYS_OF_WEEK,
    EMPLOYMENT_TYPES,
    Employee,
    ROLES,
    db,
)


bp = Blueprint('employees', __name__, url_prefix='/employees')


def _parse_time_field(value):
    if not value:
        return None
    try:
        return time.fromisoformat(value)
    except ValueError:
        return None


def _collect_availabilities_from_form():
    entries = []
    for day_index in range(7):
        start = _parse_time_field(
            (request.form.get(f'avail_{day_index}_start') or '').strip()
        )
        end = _parse_time_field(
            (request.form.get(f'avail_{day_index}_end') or '').strip()
        )
        if start and end and end > start:
            entries.append(
                Availability(day_of_week=day_index, start_time=start, end_time=end)
            )
    return entries


def _employee_snapshot(employee):
    return (
        f"{employee.name} | {employee.role} | "
        f"{employee.employment_type} | {employee.max_hours_per_week}h | "
        f"avail: {employee.availability_summary()}"
    )


@bp.route('/')
@login_required
def index():
    employees = Employee.query.order_by(Employee.role, Employee.name).all()
    return render_template('employees/index.html', employees=employees)


@bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        role = (request.form.get('role') or '').strip()
        try:
            max_hours = int(request.form.get('max_hours_per_week') or 40)
        except ValueError:
            max_hours = 40
        employment_type = request.form.get('employment_type') or 'full_time'

        if not name or role not in ROLES or employment_type not in EMPLOYMENT_TYPES:
            flash('Name, role, and employment type are required', 'error')
            return redirect(url_for('employees.new'))

        employee = Employee(
            name=name,
            role=role,
            max_hours_per_week=max_hours,
            employment_type=employment_type,
        )
        for avail in _collect_availabilities_from_form():
            employee.availabilities.append(avail)

        db.session.add(employee)
        db.session.commit()

        log_action(
            current_user,
            'create',
            'Employee',
            employee.id,
            f"Created employee: {_employee_snapshot(employee)}",
        )
        flash(f'Employee "{employee.name}" created', 'success')
        return redirect(url_for('employees.index'))

    return render_template(
        'employees/form.html',
        employee=None,
        roles=ROLES,
        days=DAYS_OF_WEEK,
        employment_types=EMPLOYMENT_TYPES,
    )


@bp.route('/<int:employee_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(employee_id):
    employee = Employee.query.get_or_404(employee_id)

    if request.method == 'POST':
        before = _employee_snapshot(employee)

        employee.name = (request.form.get('name') or employee.name).strip()
        role = (request.form.get('role') or employee.role).strip()
        if role in ROLES:
            employee.role = role
        try:
            employee.max_hours_per_week = int(
                request.form.get('max_hours_per_week') or employee.max_hours_per_week
            )
        except ValueError:
            pass
        employment_type = request.form.get('employment_type') or employee.employment_type
        if employment_type in EMPLOYMENT_TYPES:
            employee.employment_type = employment_type

        for existing in list(employee.availabilities):
            db.session.delete(existing)
        for avail in _collect_availabilities_from_form():
            employee.availabilities.append(avail)

        db.session.commit()
        after = _employee_snapshot(employee)

        log_action(
            current_user,
            'update',
            'Employee',
            employee.id,
            f"Updated employee. Before: {before} || After: {after}",
        )
        flash(f'Employee "{employee.name}" updated', 'success')
        return redirect(url_for('employees.index'))

    return render_template(
        'employees/form.html',
        employee=employee,
        roles=ROLES,
        days=DAYS_OF_WEEK,
        employment_types=EMPLOYMENT_TYPES,
    )


@bp.route('/<int:employee_id>/delete', methods=['POST'])
@login_required
def delete(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    snapshot = _employee_snapshot(employee)
    name = employee.name

    db.session.delete(employee)
    db.session.commit()

    log_action(
        current_user,
        'delete',
        'Employee',
        employee_id,
        f"Deleted employee: {snapshot}",
    )
    flash(f'Employee "{name}" deleted', 'success')
    return redirect(url_for('employees.index'))
