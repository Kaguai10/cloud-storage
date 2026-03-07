from flask import Blueprint, request, jsonify
from database import db
from models import User, File, ActivityLog
from services.auth_service import admin_required, hash_password
from services.storage import delete_file
from utils.validator import validate_email, validate_username
from utils.logger import get_logger
from datetime import datetime

admin_bp = Blueprint("admin", __name__)
logger = get_logger()


@admin_bp.route("/dashboard", methods=["GET"])
@admin_required
def admin_dashboard():
    """Get admin dashboard statistics"""
    # Count statistics
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    total_files = File.query.count()
    public_files = File.query.filter_by(visibility="public").count()
    
    # Recent activity
    recent_logs = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(10).all()
    
    # Top users by file count
    top_users = db.session.query(
        User.id, User.username, db.func.count(File.id).label("file_count")
    ).outerjoin(File).group_by(User.id).order_by(db.func.count(File.id).desc()).limit(5).all()
    
    return jsonify({
        "stats": {
            "total_users": total_users,
            "active_users": active_users,
            "inactive_users": total_users - active_users,
            "total_files": total_files,
            "public_files": public_files,
            "private_files": total_files - public_files
        },
        "recent_activity": [log.to_dict() for log in recent_logs],
        "top_users": [
            {"user_id": u.id, "username": u.username, "file_count": u.file_count}
            for u in top_users
        ]
    })


@admin_bp.route("/users", methods=["GET"])
@admin_required
def list_all_users():
    """List all users with pagination"""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    search = request.args.get("search", "")
    status = request.args.get("status", "")
    
    query = User.query
    
    # Search filter
    if search:
        query = query.filter(
            db.or_(
                User.username.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%")
            )
        )
    
    # Status filter
    if status == "active":
        query = query.filter_by(is_active=True)
    elif status == "inactive":
        query = query.filter_by(is_active=False)
    
    # Order by created_at desc
    query = query.order_by(User.created_at.desc())
    
    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    users = pagination.items
    
    return jsonify({
        "users": [user.to_dict() for user in users],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": pagination.total,
            "pages": pagination.pages,
            "has_next": pagination.has_next,
            "has_prev": pagination.has_prev
        }
    })


@admin_bp.route("/users/<int:user_id>", methods=["GET"])
@admin_required
def get_user_detail(user_id):
    """Get detailed user information"""
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Get user's files
    files = File.query.filter_by(owner_id=user_id).order_by(File.created_at.desc()).limit(20).all()
    
    # Get user's activity logs
    logs = ActivityLog.query.filter_by(user_id=user_id).order_by(ActivityLog.created_at.desc()).limit(20).all()
    
    return jsonify({
        "user": user.to_dict(),
        "files": [f.to_dict() for f in files],
        "recent_logs": [log.to_dict() for log in logs]
    })


@admin_bp.route("/users/<int:user_id>", methods=["PUT"])
@admin_required
def update_user(user_id):
    """Update user (admin)"""
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Get update data
    username = request.form.get("username")
    email = request.form.get("email")
    is_admin = request.form.get("is_admin")
    is_active = request.form.get("is_active")
    
    # Validate and update username
    if username and username != user.username:
        valid, msg = validate_username(username)
        if not valid:
            return jsonify({"error": msg}), 400
        
        if User.query.filter_by(username=username).first():
            return jsonify({"error": "Username already taken"}), 400
        
        user.username = username
    
    # Validate and update email
    if email and email != user.email:
        if not validate_email(email):
            return jsonify({"error": "Invalid email format"}), 400
        
        if User.query.filter_by(email=email).first():
            return jsonify({"error": "Email already registered"}), 400
        
        user.email = email
    
    # Update admin status
    if is_admin is not None:
        user.is_admin = is_admin.lower() in ("true", "1", "yes")
    
    # Update active status
    if is_active is not None:
        user.is_active = is_active.lower() in ("true", "1", "yes")
    
    try:
        db.session.commit()
        
        # Log activity
        log = ActivityLog(
            user_id=request.current_user["user_id"],
            action="ADMIN_USER_UPDATED",
            resource_type="user",
            resource_id=user_id,
            ip_address=request.remote_addr,
            details=f"Updated user: {user.username}",
            status="success"
        )
        db.session.add(log)
        db.session.commit()
        
        logger.info(f"Admin updated user {user_id}: {user.username}")
        
        return jsonify({
            "message": "User updated successfully",
            "user": user.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Admin user update error: {e}")
        return jsonify({"error": "Update failed"}), 500


@admin_bp.route("/users/<int:user_id>", methods=["DELETE"])
@admin_required
def delete_user(user_id):
    """Delete user (admin)"""
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Prevent self-deletion
    if user_id == request.current_user["user_id"]:
        return jsonify({"error": "Cannot delete your own account"}), 400
    
    try:
        # Delete user's files from storage
        files = File.query.filter_by(owner_id=user_id).all()
        for f in files:
            delete_file(f.object_path)
        
        # Delete user (cascade will handle related records)
        username = user.username
        db.session.delete(user)
        db.session.commit()
        
        # Log activity
        log = ActivityLog(
            user_id=request.current_user["user_id"],
            action="ADMIN_USER_DELETED",
            resource_type="user",
            resource_id=user_id,
            ip_address=request.remote_addr,
            details=f"Deleted user: {username}",
            status="success"
        )
        db.session.add(log)
        db.session.commit()
        
        logger.info(f"Admin deleted user {user_id}: {username}")
        
        return jsonify({"message": "User deleted successfully"})
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Admin user deletion error: {e}")
        return jsonify({"error": "Deletion failed"}), 500


@admin_bp.route("/users/<int:user_id>/reset-password", methods=["POST"])
@admin_required
def reset_user_password(user_id):
    """Reset user password (admin)"""
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    new_password = request.form.get("new_password")
    
    if not new_password:
        return jsonify({"error": "New password required"}), 400
    
    if len(new_password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400
    
    try:
        user.password_hash = hash_password(new_password).decode("utf-8")
        db.session.commit()
        
        # Log activity
        log = ActivityLog(
            user_id=request.current_user["user_id"],
            action="ADMIN_PASSWORD_RESET",
            resource_type="user",
            resource_id=user_id,
            ip_address=request.remote_addr,
            details=f"Password reset for: {user.username}",
            status="success"
        )
        db.session.add(log)
        db.session.commit()
        
        logger.info(f"Admin reset password for user {user_id}: {user.username}")
        
        return jsonify({"message": "Password reset successfully"})
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Admin password reset error: {e}")
        return jsonify({"error": "Password reset failed"}), 500


@admin_bp.route("/logs", methods=["GET"])
@admin_required
def get_activity_logs():
    """Get activity logs with filtering"""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    user_id = request.args.get("user_id", type=int)
    action = request.args.get("action", "")
    status = request.args.get("status", "")
    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")
    
    query = ActivityLog.query
    
    # Filters
    if user_id:
        query = query.filter_by(user_id=user_id)
    
    if action:
        query = query.filter(ActivityLog.action.ilike(f"%{action}%"))
    
    if status:
        query = query.filter_by(status=status)
    
    if date_from:
        try:
            date_from_dt = datetime.fromisoformat(date_from)
            query = query.filter(ActivityLog.created_at >= date_from_dt)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_dt = datetime.fromisoformat(date_to)
            query = query.filter(ActivityLog.created_at <= date_to_dt)
        except ValueError:
            pass
    
    # Order by created_at desc
    query = query.order_by(ActivityLog.created_at.desc())
    
    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    logs = pagination.items
    
    return jsonify({
        "logs": [log.to_dict() for log in logs],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": pagination.total,
            "pages": pagination.pages,
            "has_next": pagination.has_next,
            "has_prev": pagination.has_prev
        }
    })


@admin_bp.route("/files", methods=["GET"])
@admin_required
def list_all_files():
    """List all PUBLIC files with filtering"""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    search = request.args.get("search", "")

    # Admin can ONLY see public files
    query = File.query.filter_by(visibility="public")

    # Search filter
    if search:
        query = query.filter(
            db.or_(
                File.filename.ilike(f"%{search}%"),
                File.original_filename.ilike(f"%{search}%")
            )
        )

    # Order by created_at desc
    query = query.order_by(File.created_at.desc())

    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    files = pagination.items

    return jsonify({
        "files": [f.to_dict() for f in files],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": pagination.total,
            "pages": pagination.pages,
            "has_next": pagination.has_next,
            "has_prev": pagination.has_prev
        }
    })


@admin_bp.route("/files/<int:file_id>", methods=["DELETE"])
@admin_required
def delete_file_admin(file_id):
    """Delete PUBLIC file (admin)"""
    file = File.query.get(file_id)

    if not file:
        return jsonify({"error": "File not found"}), 404

    # Admin can ONLY delete public files
    if file.visibility != "public":
        return jsonify({"error": "Access denied. Admin can only delete public files."}), 403

    try:
        # Delete from storage
        delete_file(file.object_path)

        filename = file.filename
        db.session.delete(file)
        db.session.commit()

        # Log activity
        log = ActivityLog(
            user_id=request.current_user["user_id"],
            action="ADMIN_FILE_DELETED",
            resource_type="file",
            resource_id=file_id,
            ip_address=request.remote_addr,
            details=f"Deleted public file: {filename}",
            status="success"
        )
        db.session.add(log)
        db.session.commit()

        logger.info(f"Admin deleted public file {file_id}: {filename}")

        return jsonify({"message": "File deleted successfully"})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Admin file deletion error: {e}")
        return jsonify({"error": "Deletion failed"}), 500
