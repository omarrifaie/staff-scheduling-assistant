from datetime import timedelta

from .models import Assignment, Employee, Shift, db


def _employee_available_for_shift(employee, shift):
    day = shift.date.weekday()
    for avail in employee.availabilities:
        if avail.day_of_week != day:
            continue
        if avail.start_time <= shift.start_time and avail.end_time >= shift.end_time:
            return True
    return False


def _times_overlap(a_start, a_end, b_start, b_end):
    return not (a_end <= b_start or a_start >= b_end)


def generate_schedule(start_date, end_date):
    """Clear existing assignments in the range and auto assign employees to shifts.

    Returns a summary dict with counts and conflicts.
    """
    shifts = (
        Shift.query
        .filter(Shift.date >= start_date, Shift.date <= end_date)
        .order_by(Shift.date, Shift.start_time)
        .all()
    )
    shift_ids = [s.id for s in shifts]

    if shift_ids:
        Assignment.query.filter(Assignment.shift_id.in_(shift_ids)).delete(
            synchronize_session=False
        )
        db.session.commit()

    employees = Employee.query.order_by(Employee.name).all()

    weekly_hours = {e.id: 0.0 for e in employees}
    day_bookings = {}
    created = 0

    for shift in shifts:
        shift_hours = shift.duration_hours()
        eligible = []

        for emp in employees:
            if emp.role != shift.required_role:
                continue
            if not _employee_available_for_shift(emp, shift):
                continue
            if weekly_hours[emp.id] + shift_hours > emp.max_hours_per_week + 0.001:
                continue

            bookings_today = day_bookings.get((emp.id, shift.date), [])
            conflict = False
            for bs, be in bookings_today:
                if _times_overlap(shift.start_time, shift.end_time, bs, be):
                    conflict = True
                    break
            if conflict:
                continue

            eligible.append(emp)

        eligible.sort(
            key=lambda e: (
                weekly_hours[e.id],
                0 if e.employment_type == 'full_time' else 1,
                e.name,
            )
        )

        for emp in eligible[: shift.min_staff]:
            assignment = Assignment(shift_id=shift.id, employee_id=emp.id)
            db.session.add(assignment)
            weekly_hours[emp.id] += shift_hours
            day_bookings.setdefault((emp.id, shift.date), []).append(
                (shift.start_time, shift.end_time)
            )
            created += 1

    db.session.commit()

    conflicts = detect_conflicts(start_date, end_date)

    return {
        'assignments_created': created,
        'shift_count': len(shifts),
        'conflicts': conflicts,
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
    }


def detect_conflicts(start_date, end_date):
    """Return conflicts for the shifts in the given date range.

    Conflict types:
      understaffed  : shift assigned fewer employees than min_staff
      double_booking: employee assigned to overlapping shifts on the same day
    """
    shifts = (
        Shift.query
        .filter(Shift.date >= start_date, Shift.date <= end_date)
        .order_by(Shift.date, Shift.start_time)
        .all()
    )

    conflicts = []
    employee_entries = {}

    for shift in shifts:
        assigned = shift.assignments
        if len(assigned) < shift.min_staff:
            conflicts.append({
                'type': 'understaffed',
                'shift_id': shift.id,
                'shift_label': (
                    f"{shift.date.isoformat()} "
                    f"{shift.start_time.strftime('%H:%M')}-"
                    f"{shift.end_time.strftime('%H:%M')} "
                    f"({shift.required_role})"
                ),
                'assigned_count': len(assigned),
                'required': shift.min_staff,
            })
        for a in assigned:
            employee_entries.setdefault(a.employee_id, []).append((shift, a))

    for employee_id, entries in employee_entries.items():
        entries.sort(key=lambda pair: (pair[0].date, pair[0].start_time))
        for i in range(len(entries)):
            shift_i, _ = entries[i]
            for j in range(i + 1, len(entries)):
                shift_j, _ = entries[j]
                if shift_j.date != shift_i.date:
                    break
                if _times_overlap(
                    shift_i.start_time, shift_i.end_time,
                    shift_j.start_time, shift_j.end_time,
                ):
                    employee = Employee.query.get(employee_id)
                    employee_name = employee.name if employee else 'Unknown'
                    conflicts.append({
                        'type': 'double_booking',
                        'employee_id': employee_id,
                        'employee_name': employee_name,
                        'shift_ids': [shift_i.id, shift_j.id],
                        'description': (
                            f"{employee_name} is booked on {shift_i.date.isoformat()} "
                            f"for {shift_i.start_time.strftime('%H:%M')}-"
                            f"{shift_i.end_time.strftime('%H:%M')} and "
                            f"{shift_j.start_time.strftime('%H:%M')}-"
                            f"{shift_j.end_time.strftime('%H:%M')}"
                        ),
                    })

    return conflicts


def can_assign(employee, shift):
    """Return (ok, reason) indicating whether this employee can take this shift."""
    if employee.role != shift.required_role:
        return False, f"Role mismatch: employee is {employee.role}, shift requires {shift.required_role}"

    if not _employee_available_for_shift(employee, shift):
        return False, "Employee is not available during this shift window"

    for a in employee.assignments:
        if a.shift_id == shift.id:
            continue
        if a.shift.date != shift.date:
            continue
        if _times_overlap(
            shift.start_time, shift.end_time,
            a.shift.start_time, a.shift.end_time,
        ):
            return False, "Double booking with an existing assignment on the same day"

    week_start = shift.date - timedelta(days=shift.date.weekday())
    week_end = week_start + timedelta(days=6)
    existing_hours = sum(
        a.shift.duration_hours()
        for a in employee.assignments
        if a.shift_id != shift.id and week_start <= a.shift.date <= week_end
    )
    if existing_hours + shift.duration_hours() > employee.max_hours_per_week + 0.001:
        return False, "Assigning would exceed the employee's weekly max hours"

    return True, "OK"
