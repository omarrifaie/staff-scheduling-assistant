"""Populate the database with a default admin, 16 sample employees,
a full week of sample shifts, and an auto generated schedule.

Run with: python seed.py
"""
from datetime import date, time, timedelta

from app import create_app
from app.audit_helpers import log_action
from app.models import AdminUser, Availability, Employee, Shift, db
from app.scheduler import generate_schedule


EMPLOYEES = [
    {'name': 'Alice Morgan',       'role': 'Manager', 'max_hours': 40, 'type': 'full_time', 'pattern': 'weekdays_opening'},
    {'name': 'Benjamin Clarke',    'role': 'Manager', 'max_hours': 40, 'type': 'full_time', 'pattern': 'weekdays_closing'},
    {'name': 'Catherine Liu',      'role': 'Manager', 'max_hours': 32, 'type': 'part_time', 'pattern': 'weekends_full'},
    {'name': 'Quinn Raymond',      'role': 'Manager', 'max_hours': 14, 'type': 'part_time', 'pattern': 'weekends_evening'},
    {'name': 'Daniel Rivera',      'role': 'Cook',    'max_hours': 40, 'type': 'full_time', 'pattern': 'weekdays_opening'},
    {'name': 'Emma Schultz',       'role': 'Cook',    'max_hours': 40, 'type': 'full_time', 'pattern': 'weekdays_closing'},
    {'name': 'Felix Andersen',     'role': 'Cook',    'max_hours': 28, 'type': 'part_time', 'pattern': 'weekends_full'},
    {'name': 'Grace Huang',        'role': 'Server',  'max_hours': 20, 'type': 'part_time', 'pattern': 'mon_wed_fri'},
    {'name': 'Henry Patel',        'role': 'Server',  'max_hours': 25, 'type': 'part_time', 'pattern': 'tue_thu_sat'},
    {'name': 'Isabelle Novak',     'role': 'Server',  'max_hours': 40, 'type': 'full_time', 'pattern': 'weekdays_full'},
    {'name': 'Priya Chatterjee',   'role': 'Server',  'max_hours': 30, 'type': 'part_time', 'pattern': 'all_week_late'},
    {'name': 'Jacob Thompson',     'role': 'Cashier', 'max_hours': 25, 'type': 'part_time', 'pattern': 'mon_wed_fri'},
    {'name': 'Katelyn Park',       'role': 'Cashier', 'max_hours': 25, 'type': 'part_time', 'pattern': 'tue_thu_sat'},
    {'name': 'Liam Brooks',        'role': 'Cashier', 'max_hours': 40, 'type': 'full_time', 'pattern': 'weekdays_closing'},
    {'name': 'Rachel Nguyen',      'role': 'Cashier', 'max_hours': 24, 'type': 'part_time', 'pattern': 'weekends_full'},
    {'name': 'Maya Delgado',       'role': 'Barista', 'max_hours': 25, 'type': 'part_time', 'pattern': 'weekdays_opening'},
    {'name': 'Noah Fitzgerald',    'role': 'Barista', 'max_hours': 40, 'type': 'full_time', 'pattern': 'all_week_opening'},
    {'name': 'Olivia Reyes',       'role': 'Barista', 'max_hours': 20, 'type': 'part_time', 'pattern': 'weekends_full'},
]


AVAILABILITY_PATTERNS = {
    # Monday to Friday, 6am to 6pm
    'weekdays_opening': [(d, 6, 18) for d in range(5)],
    # Monday to Friday, 12pm to 11pm
    'weekdays_closing': [(d, 12, 23) for d in range(5)],
    # Monday to Friday, 6am to 11pm
    'weekdays_full': [(d, 6, 23) for d in range(5)],
    # Saturday and Sunday, 6am to 11pm
    'weekends_full': [(5, 6, 23), (6, 6, 23)],
    # Saturday and Sunday, 2pm to 11pm (evening focused weekend)
    'weekends_evening': [(5, 14, 23), (6, 14, 23)],
    # Every day, 6am to 6pm
    'all_week_opening': [(d, 6, 18) for d in range(7)],
    # Every day, 11am to 11pm (late morning onward)
    'all_week_late': [(d, 11, 23) for d in range(7)],
    # Monday, Wednesday, Friday, 7am to 10pm
    'mon_wed_fri': [(0, 7, 22), (2, 7, 22), (4, 7, 22)],
    # Tuesday, Thursday, Saturday, 7am to 10pm
    'tue_thu_sat': [(1, 7, 22), (3, 7, 22), (5, 7, 22)],
}


def _availabilities_for(pattern_name):
    pattern = AVAILABILITY_PATTERNS[pattern_name]
    return [
        Availability(
            day_of_week=day,
            start_time=time(start_hour, 0),
            end_time=time(end_hour, 0),
        )
        for (day, start_hour, end_hour) in pattern
    ]


DAILY_SHIFT_TEMPLATES = [
    # (start_hour, end_hour, role, min_staff, notes)
    (7,  11, 'Barista', 2, 'Morning coffee rush'),
    (8,  12, 'Cashier', 1, 'Opening cashier'),
    (10, 14, 'Cook',    1, 'Lunch prep and service'),
    (11, 15, 'Server',  1, 'Lunch floor'),
    (9,  17, 'Manager', 1, 'Day manager on duty'),
    (14, 22, 'Cook',    1, 'Dinner line'),
    (16, 22, 'Server',  1, 'Dinner floor'),
    (14, 22, 'Cashier', 1, 'Evening cashier'),
    (15, 22, 'Manager', 1, 'Evening manager on duty'),
]


def _build_week_shifts(monday):
    shifts = []
    for day_offset in range(7):
        shift_date = monday + timedelta(days=day_offset)
        for (start_hour, end_hour, role, min_staff, notes) in DAILY_SHIFT_TEMPLATES:
            shifts.append(Shift(
                date=shift_date,
                start_time=time(start_hour, 0),
                end_time=time(end_hour, 0),
                required_role=role,
                min_staff=min_staff,
                notes=notes,
            ))
    return shifts


def seed():
    app = create_app()
    with app.app_context():
        print('Resetting database...')
        db.drop_all()
        db.create_all()

        print('Creating admin user (username: admin, password: admin123)...')
        admin = AdminUser(username='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()

        print(f'Creating {len(EMPLOYEES)} employees...')
        for spec in EMPLOYEES:
            employee = Employee(
                name=spec['name'],
                role=spec['role'],
                max_hours_per_week=spec['max_hours'],
                employment_type=spec['type'],
            )
            for avail in _availabilities_for(spec['pattern']):
                employee.availabilities.append(avail)
            db.session.add(employee)
        db.session.commit()

        today = date.today()
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)
        shifts = _build_week_shifts(monday)

        print(f'Creating {len(shifts)} shifts for week of {monday.isoformat()}...')
        db.session.add_all(shifts)
        db.session.commit()

        log_action(
            admin,
            'seed',
            'System',
            None,
            (
                f"Seeded database with {len(EMPLOYEES)} employees and "
                f"{len(shifts)} shifts for {monday.isoformat()} through {sunday.isoformat()}"
            ),
        )

        print('Running auto scheduler for the week...')
        result = generate_schedule(monday, sunday)
        log_action(
            admin,
            'generate',
            'Schedule',
            None,
            (
                f"Initial auto generated schedule for {monday.isoformat()} through "
                f"{sunday.isoformat()}: {result['assignments_created']} assignments, "
                f"{len(result['conflicts'])} conflict(s)"
            ),
        )

        print()
        print('Seed complete.')
        print(f"  Employees:   {len(EMPLOYEES)}")
        print(f"  Shifts:      {len(shifts)} (week of {monday.isoformat()})")
        print(f"  Assignments: {result['assignments_created']}")
        print(f"  Conflicts:   {len(result['conflicts'])}")
        print()
        print('Start the app with: flask run')
        print('Then sign in at http://127.0.0.1:5000 with admin / admin123')


if __name__ == '__main__':
    seed()
