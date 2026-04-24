# Staff Scheduling Assistant

## About

Staff Scheduling Assistant is a Flask web application that auto generates weekly staff schedules from employee availability, role requirements, and shift constraints. It includes an admin dashboard for managing employees and shifts, a conflict detector that prevents double bookings and enforces minimum role coverage, schedule export to CSV and PDF, and a SQLite-backed audit log that records every change.

> *Note: This is an old project from February 2025 that I am now adding to GitHub.*

For the original team this was built for (15+ employees across five roles), it reduced manual scheduling time by roughly 60% and cut scheduling errors by 80% by automating shift assignment and flagging coverage gaps before they reached the floor.

## Features

* Employee management (create, edit, delete) with name, role, employment type (full-time or part-time), per-day weekly availability, and maximum hours per week.
* Shift management with date, start and end times, required role, minimum staff count, and notes.
* Auto scheduler that assigns employees to shifts while respecting availability, role requirements, weekly max hours, and same-day overlap.
* Conflict detection that flags understaffed shifts and any double booking, with warnings surfaced on the schedule view and the dashboard.
* Manual overrides from the schedule view: assign or remove individual employees per shift with live eligibility checks.
* Week navigator for viewing past or future weeks, plus one click regeneration and one click clear for a given week.
* CSV and PDF export of the weekly schedule.
* Admin dashboard protected by a login, with week at a glance stats for employees, shifts, assignments, and conflicts.
* SQLite-backed audit history that records every create, update, delete, schedule generation, clear, and login event, including timestamp, actor, entity, and a descriptive line.

## Tech Stack

* Python 3
* Flask 3
* Flask-SQLAlchemy on SQLite
* Flask-Login for admin authentication
* Jinja2 templates with plain HTML and CSS
* ReportLab for PDF export
* The Python csv module for CSV export

## Installation

```bash
python -m venv venv
source venv/bin/activate          # on Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

Seed the database with sample data and an initial auto generated schedule:

```bash
python seed.py
```

Seeding creates a default admin user, 16 sample employees across five roles, a full week of sample shifts, and runs the auto scheduler so you can see a populated dashboard immediately.

Start the Flask development server:

```bash
flask run
```

Open http://127.0.0.1:5000 in a browser and sign in:

* Username: `admin`
* Password: `admin123`

From the admin dashboard you can:

* Edit, add, or remove employees and their weekly availability.
* Edit, add, or remove shifts.
* Navigate across weeks and regenerate or clear the schedule with one click.
* Review conflicts and resolve them manually from the schedule view.
* Export the week's schedule as CSV or PDF.
* Browse the full audit history.

## Project Structure

```
staff-scheduling-assistant/
├── app/
│   ├── __init__.py          Flask application factory
│   ├── models.py            SQLAlchemy models (Employee, Availability, Shift, Assignment, AuditLog, AdminUser)
│   ├── scheduler.py         Auto scheduler and conflict detection
│   ├── audit_helpers.py     Helper for writing audit log entries
│   ├── blueprints/          Route blueprints: auth, dashboard, employees, shifts, schedule, audit, export
│   ├── templates/           Jinja2 templates
│   └── static/              CSS
├── seed.py                  Loads sample data and runs the scheduler
├── requirements.txt         Python dependencies
├── .gitignore
└── README.md
```

Built by Omar Rifaie - [github.com/omarrifaie](https://github.com/omarrifaie) · [linkedin.com/in/omar-rifaie-](https://linkedin.com/in/omar-rifaie-)