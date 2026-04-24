import os

from flask import Flask, redirect, url_for
from flask_login import LoginManager, current_user

from .models import AdminUser, db


login_manager = LoginManager()
login_manager.login_view = 'auth.login'


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('FLASK_SECRET_KEY', 'change-this-in-production'),
        SQLALCHEMY_DATABASE_URI=(
            'sqlite:///'
            + os.path.join(app.instance_path, 'scheduling.db').replace('\\', '/')
        ),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    if test_config:
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return AdminUser.query.get(int(user_id))

    from .blueprints.audit import bp as audit_bp
    from .blueprints.auth import bp as auth_bp
    from .blueprints.dashboard import bp as dashboard_bp
    from .blueprints.employees import bp as employees_bp
    from .blueprints.export import bp as export_bp
    from .blueprints.schedule import bp as schedule_bp
    from .blueprints.shifts import bp as shifts_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(employees_bp)
    app.register_blueprint(shifts_bp)
    app.register_blueprint(schedule_bp)
    app.register_blueprint(audit_bp)
    app.register_blueprint(export_bp)

    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard.index'))
        return redirect(url_for('auth.login'))

    with app.app_context():
        db.create_all()

    return app
