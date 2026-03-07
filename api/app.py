from flask import Flask, request, jsonify
from flask_cors import CORS
from config import Config
from database import db, init_db
from utils.logger import setup_logger, get_logger
from utils.captcha import init_captcha_db
import os

# Blueprints
from routes.auth import auth_bp
from routes.users import users_bp
from routes.admin import admin_bp
from routes.files import files_bp
from routes.search import search_bp
from health import health_bp
from services.minio_init import init_minio


def create_default_admin():
    """Create default admin user if not exists"""
    from models import User
    from services.auth_service import hash_password

    try:
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@cloudstorage.local',
                password_hash=hash_password('admin123').decode('utf-8'),
                profile_photo=None,
                is_admin=True,
                is_active=True
            )
            db.session.add(admin)
            db.session.commit()
            logger = get_logger()
            logger.info("Default admin user created: admin / admin123")
        else:
            logger = get_logger()
            logger.info(f"Admin user exists: {admin.username}")
    except Exception as e:
        logger = get_logger()
        logger.error(f"Error creating admin user: {e}")
        db.session.rollback()


def create_app(config_class=Config):
    """Application factory for creating Flask app"""

    app = Flask(__name__)
    app.config.from_object(config_class)

    # Set SQLAlchemy config key (Flask-SQLAlchemy requires this specific key)
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config.get('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize extensions
    CORS(app)
    db.init_app(app)

    # Create logs directory
    os.makedirs(app.config.get("LOG_DIR", "/app/logs"), exist_ok=True)

    # Setup logger
    setup_logger(app)
    logger = get_logger()

    # Register blueprints
    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp, url_prefix="/api")
    app.register_blueprint(users_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    app.register_blueprint(files_bp, url_prefix="/api/files")
    app.register_blueprint(search_bp, url_prefix="/api/search")

    # Create tables and initialize data
    with app.app_context():
        try:
            db.create_all()
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
            raise
        
        try:
            init_captcha_db()
            logger.info("Captcha database initialized")
        except Exception as e:
            logger.warning(f"Captcha initialization skipped: {e}")
        
        try:
            init_minio()
            logger.info("MinIO initialized")
        except Exception as e:
            logger.error(f"MinIO initialization failed: {e}")
        
        try:
            create_default_admin()
            logger.info("Default admin user setup completed")
        except Exception as e:
            logger.error(f"Error creating admin user: {e}")

    # Request logging middleware
    @app.before_request
    def log_request():
        logger = get_logger()
        logger.info(f"{request.method} {request.path} from {request.remote_addr}")

    # Error handlers
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({"error": "Bad request", "message": str(error)}), 400

    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({"error": "Unauthorized", "message": "Authentication required"}), 401

    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({"error": "Forbidden", "message": "Access denied"}), 403

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Not found", "message": "Resource not found"}), 404

    @app.errorhandler(500)
    def internal_error(error):
        logger = get_logger()
        logger.error(f"Internal error: {error}")
        return jsonify({"error": "Internal server error"}), 500

    return app


if __name__ == "__main__":
    app = create_app()
    logger = get_logger()
    logger.info("Starting Mini Cloud Storage API on port 8080")
    app.run(host="0.0.0.0", port=8080, debug=app.config.get("DEBUG", False))
