
from pathlib import Path
import warnings
import threading
import time

from flask import Flask, request, send_from_directory
from PIL import Image
from flask_cors import CORS

from config import Config
from server.blueprints.role_permissions import role_permissions_bp
from server.blueprints.login_register import login_register_bp
from server.blueprints.profile import profile_bp
from server.blueprints.care_methods import care_methods_bp
from server.blueprints.care_reminders import care_reminders_bp
from server.blueprints.home import home_bp, health_bp
from server.blueprints.feedback_center import feedback_center_bp
from server.blueprints.zone_location import location_bp
from server.blueprints.operation_logs import operation_logs_bp
from server.blueprints.plant_management import plant_management_bp
from server.blueprints.photo_recognition import photo_recognition_bp
from server.blueprints.plant_species import plant_species_bp
from server.blueprints.user_management import user_management_bp
from server.common import ensure_system_catalog
from server.db import close_db
from server.errors import register_error_handlers
from server.logger import init_ip_location_service
from server.blueprints.care_reminder_engine import run_care_reminder_engine
from server.cache import redis_request_stats


def start_care_scheduler(app: Flask) -> None:
    interval_seconds = float(app.config.get('CARE_REMINDER_REFRESH_SECONDS', 15) or 15)
    interval_seconds = max(1.0, interval_seconds)

    def runner() -> None:
        with app.app_context():
            try:
                run_care_reminder_engine('startup')
            except Exception:
                app.logger.exception('care reminder init failed')
        while True:
            time.sleep(interval_seconds)
            with app.app_context():
                try:
                    run_care_reminder_engine('scheduler')
                except Exception:
                    app.logger.exception('care reminder scheduled refresh failed')

    if app.config.get('ENABLE_CARE_SCHEDULER', True) and not app.extensions.get('care_scheduler_started'):
        thread = threading.Thread(target=runner, name='care-reminder-scheduler', daemon=True)
        thread.start()
        app.extensions['care_scheduler_started'] = True


def _cors_origins(app: Flask):

    return '*'


def create_app() -> Flask:
    app = Flask(__name__, static_folder=None)
    app.config.from_object(Config)
    Image.MAX_IMAGE_PIXELS = int(app.config.get('UPLOAD_IMAGE_MAX_PIXELS', 80_000_000) or 80_000_000)
    warnings.simplefilter('error', Image.DecompressionBombWarning)


    app.config.setdefault('DB_HOST', app.config.get('MYSQL_HOST', '127.0.0.1'))
    app.config.setdefault('DB_PORT', app.config.get('MYSQL_PORT', 3306))
    app.config.setdefault('DB_USER', app.config.get('MYSQL_USER', 'root'))
    app.config.setdefault('DB_PASSWORD', app.config.get('MYSQL_PASSWORD', ''))
    app.config.setdefault('DB_NAME', app.config.get('MYSQL_DATABASE', 'Plants_Recognition'))

    Path(app.config['UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)


    CORS(app, resources={r'/api/*': {'origins': _cors_origins(app)}}, supports_credentials=False, methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'], allow_headers='*')

    init_ip_location_service(app)
    app.teardown_appcontext(close_db)
    register_error_handlers(app)

    with app.app_context():
        ensure_system_catalog()

    start_care_scheduler(app)


    app.register_blueprint(login_register_bp, url_prefix='/api/auth')
    app.register_blueprint(profile_bp, url_prefix='/api/auth')
    app.register_blueprint(home_bp, url_prefix='/api/dashboard')
    app.register_blueprint(photo_recognition_bp, url_prefix='/api/recognitions')
    app.register_blueprint(plant_species_bp, url_prefix='/api/species')
    app.register_blueprint(plant_management_bp, url_prefix='/api/plants')
    app.register_blueprint(location_bp, url_prefix='/api/locations')
    app.register_blueprint(care_methods_bp, url_prefix='/api/care')
    app.register_blueprint(care_reminders_bp, url_prefix='/api/care')
    app.register_blueprint(feedback_center_bp, url_prefix='/api/feedbacks')
    app.register_blueprint(user_management_bp, url_prefix='/api/users')
    app.register_blueprint(operation_logs_bp, url_prefix='/api/logs')
    app.register_blueprint(role_permissions_bp, url_prefix='/api/access')
    app.register_blueprint(health_bp, url_prefix='/api/health')

    @app.route('/uploads/<path:filename>')
    def uploaded_file(filename: str):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


    @app.after_request
    def add_headers(response):
        if request.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store'
            stats = redis_request_stats()
            if stats.get('hits') or stats.get('misses') or stats.get('stores') or stats.get('invalidations') or stats.get('errors'):
                response.headers['X-Redis-Selective-Cache'] = 'hits={hits};misses={misses};stores={stores};invalidations={invalidations};errors={errors}'.format(**stats)
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['X-XSS-Protection'] = '0'
        return response

    return app
