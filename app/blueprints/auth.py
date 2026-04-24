from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required, login_user, logout_user

from ..audit_helpers import log_action
from ..models import AdminUser


bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''
        user = AdminUser.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            log_action(user, 'login', 'AdminUser', user.id, f"{user.username} signed in")
            next_url = request.args.get('next') or url_for('dashboard.index')
            return redirect(next_url)
        flash('Invalid username or password', 'error')
    return render_template('auth/login.html')


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been signed out', 'success')
    return redirect(url_for('auth.login'))
