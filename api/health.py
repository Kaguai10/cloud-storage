from flask import Blueprint, jsonify
from database import db
from models import User, File
import psycopg2

health_bp = Blueprint("health", __name__)


@health_bp.route("/health")
def health():
    """Health check endpoint"""
    health_status = {
        "status": "ok",
        "service": "api",
        "version": "2.0"
    }
    
    # Check database connection
    try:
        db.session.execute(db.text("SELECT 1"))
        health_status["database"] = "connected"
    except Exception as e:
        health_status["database"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    return jsonify(health_status)


@health_bp.route("/stats")
def stats():
    """Get service statistics"""
    return jsonify({
        "total_users": User.query.count(),
        "total_files": File.query.count()
    })
