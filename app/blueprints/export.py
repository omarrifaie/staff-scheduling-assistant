import csv
import io
from datetime import date as date_type, timedelta

from flask import Blueprint, Response, request
from flask_login import login_required
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ..models import Shift


bp = Blueprint('export', __name__, url_prefix='/export')


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


def _build_rows(start, end):
    shifts = (
        Shift.query
        .filter(Shift.date >= start, Shift.date <= end)
        .order_by(Shift.date, Shift.start_time)
        .all()
    )
    rows = []
    for shift in shifts:
        if shift.assignments:
            for assignment in shift.assignments:
                employee = assignment.employee
                rows.append([
                    shift.date.isoformat(),
                    shift.date.strftime('%A'),
                    shift.start_time.strftime('%H:%M'),
                    shift.end_time.strftime('%H:%M'),
                    shift.required_role,
                    employee.name,
                    employee.employment_type.replace('_', ' '),
                    shift.notes or '',
                ])
        else:
            rows.append([
                shift.date.isoformat(),
                shift.date.strftime('%A'),
                shift.start_time.strftime('%H:%M'),
                shift.end_time.strftime('%H:%M'),
                shift.required_role,
                '(unassigned)',
                '',
                shift.notes or '',
            ])
    return rows


@bp.route('/csv')
@login_required
def export_csv():
    start, end = _parse_week(request.args.get('week_start'))
    rows = _build_rows(start, end)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        'Date', 'Day', 'Start', 'End', 'Role', 'Employee', 'Employment Type', 'Notes',
    ])
    for row in rows:
        writer.writerow(row)

    filename = f'schedule_{start.isoformat()}_to_{end.isoformat()}.csv'
    response = Response(buffer.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response


@bp.route('/pdf')
@login_required
def export_pdf():
    start, end = _parse_week(request.args.get('week_start'))
    rows = _build_rows(start, end)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        topMargin=0.4 * inch,
        bottomMargin=0.4 * inch,
        leftMargin=0.4 * inch,
        rightMargin=0.4 * inch,
    )

    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph(
        f"Weekly Schedule: {start.isoformat()} through {end.isoformat()}",
        styles['Title'],
    ))
    story.append(Spacer(1, 10))

    table_data = [
        ['Date', 'Day', 'Start', 'End', 'Role', 'Employee', 'Type', 'Notes'],
    ] + rows

    if not rows:
        table_data.append(['', '', '', '', '', 'No shifts in range', '', ''])

    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f2937')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#d1d5db')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f3f4f6')]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(table)

    doc.build(story)
    pdf_bytes = buffer.getvalue()

    filename = f'schedule_{start.isoformat()}_to_{end.isoformat()}.pdf'
    response = Response(pdf_bytes, mimetype='application/pdf')
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response
