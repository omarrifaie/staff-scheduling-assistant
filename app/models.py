from datetime import datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash


db = SQLAlchemy()


ROLES = ['Manager', 'Cook', 'Server', 'Cashier', 'Barista']
EMPLOYMENT_TYPES = ['full_time', 'part_time']
DAYS_OF_WEEK = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']


class Employee(db.Model):
    __tablename__ = 'employees'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    max_hours_per_week = db.Column(db.Integer, nullable=False, default=40)
    employment_type = db.Column(db.String(20), nullable=False, default='full_time')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    availabilities = db.relationship(
        'Availability',
        backref='employee',
        cascade='all, delete-orphan',
        lazy='joined',
    )
    assignments = db.relationship(
        'Assignment',
        backref='employee',
        cascade='all, delete-orphan',
        lazy='select',
    )

    def availability_summary(self):
        parts = []
        for a in sorted(self.availabilities, key=lambda x: x.day_of_week):
            parts.append(
                f"{DAYS_OF_WEEK[a.day_of_week][:3]} "
                f"{a.start_time.strftime('%H:%M')}-{a.end_time.strftime('%H:%M')}"
            )
        return ", ".join(parts) if parts else "No availability set"

    def employment_type_label(self):
        return self.employment_type.replace('_', ' ').title()


class Availability(db.Model):
    __tablename__ = 'availabilities'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(
        db.Integer,
        db.ForeignKey('employees.id', ondelete='CASCADE'),
        nullable=False,
    )
    day_of_week = db.Column(db.Integer, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)


class Shift(db.Model):
    __tablename__ = 'shifts'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, index=True)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    required_role = db.Column(db.String(50), nullable=False)
    min_staff = db.Column(db.Integer, nullable=False, default=1)
    notes = db.Column(db.String(250), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    assignments = db.relationship(
        'Assignment',
        backref='shift',
        cascade='all, delete-orphan',
        lazy='joined',
    )

    def duration_hours(self):
        start = datetime.combine(self.date, self.start_time)
        end = datetime.combine(self.date, self.end_time)
        return (end - start).total_seconds() / 3600.0

    def is_understaffed(self):
        return len(self.assignments) < self.min_staff


class Assignment(db.Model):
    __tablename__ = 'assignments'

    id = db.Column(db.Integer, primary_key=True)
    shift_id = db.Column(
        db.Integer,
        db.ForeignKey('shifts.id', ondelete='CASCADE'),
        nullable=False,
    )
    employee_id = db.Column(
        db.Integer,
        db.ForeignKey('employees.id', ondelete='CASCADE'),
        nullable=False,
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class AuditLog(db.Model):
    __tablename__ = 'audit_log'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    actor = db.Column(db.String(120), nullable=False, default='system')
    action = db.Column(db.String(30), nullable=False)
    entity_type = db.Column(db.String(50), nullable=False)
    entity_id = db.Column(db.Integer)
    description = db.Column(db.Text, default='')


class AdminUser(UserMixin, db.Model):
    __tablename__ = 'admin_users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
