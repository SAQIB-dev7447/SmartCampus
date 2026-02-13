import os
from flask import Flask, session
from . import db
from .utils import date_format, time_since, initial_filter, to_ist

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='smartcampus-secret-key-prod',
        DATABASE=os.path.join(app.instance_path, 'smartcampus.sqlite'),
        UPLOAD_FOLDER=os.path.join(app.static_folder, 'uploads'),
        MAX_CONTENT_LENGTH=16 * 1024 * 1024
    )

    if test_config is None:
        app.config.from_pyfile('config.py', silent=True)
    else:
        app.config.from_mapping(test_config)

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    db.init_app(app)

    # Register Filters
    app.jinja_env.filters['to_ist'] = to_ist
    app.jinja_env.filters['datefmt'] = date_format
    app.jinja_env.filters['timesince'] = time_since
    app.jinja_env.filters['initials'] = initial_filter

    # Context Processor for Notifications
    @app.context_processor
    def inject_notifications():
        if 'user_id' in session:
            conn = db.get_db()
            count = conn.execute(
                "SELECT COUNT(*) FROM notifications WHERE user_id = ? AND is_read = 0",
                (session['user_id'],)
            ).fetchone()[0]
            return dict(unread_count=count)
        return dict(unread_count=0)

    # Register Blueprints
    from .routes import auth, student, admin, common
    app.register_blueprint(auth.bp)
    app.register_blueprint(student.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(common.bp)

    # Default route
    @app.route('/')
    def index():
        return redirect(url_for('auth.login'))
        
    from flask import redirect, url_for

    return app
