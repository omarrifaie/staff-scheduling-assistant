from flask import Blueprint, render_template, request
from flask_login import login_required

from ..models import AuditLog


bp = Blueprint('audit', __name__, url_prefix='/audit')


@bp.route('/')
@login_required
def index():
    try:
        page = max(1, int(request.args.get('page', 1)))
    except ValueError:
        page = 1

    per_page = 50
    query = AuditLog.query.order_by(AuditLog.timestamp.desc())
    total = query.count()
    entries = query.offset((page - 1) * per_page).limit(per_page).all()
    total_pages = max(1, (total + per_page - 1) // per_page)

    return render_template(
        'audit/index.html',
        entries=entries,
        page=page,
        total_pages=total_pages,
        total=total,
    )
