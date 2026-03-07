from flask import Blueprint, request, jsonify
from database import db
from models import User, File, ActivityLog
from services.auth_service import token_required, hash_password, verify_password, decode_token
from services.storage import upload_file, delete_file, generate_object_path, get_public_url
from utils.validator import validate_email, validate_username, validate_password, validate_image_file, sanitize_filename
from utils.logger import get_logger
from config import Config

users_bp = Blueprint("users", __name__)
logger = get_logger()


@users_bp.route("/users/me", methods=["GET"])
@token_required
def get_current_user():
    """Get current user profile"""
    current_user = request.current_user
    
    user = User.query.get(current_user["user_id"])
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    return jsonify({
        "user": user.to_dict()
    })


@users_bp.route("/users/me", methods=["PUT"])
@token_required
def update_current_user():
    """Update current user profile"""
    current_user = request.current_user

    user = User.query.get(current_user["user_id"])
    if not user:
        return jsonify({"error": "User not found"}), 404

    # Get update data
    username = request.form.get("username")
    email = request.form.get("email")

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

    # Handle profile photo upload
    if "profile_photo" in request.files:
        photo = request.files["profile_photo"]
        if photo and photo.filename:
            valid, msg = validate_image_file(photo, Config.ALLOWED_EXTENSIONS, Config.MAX_UPLOAD_SIZE)
            if valid:
                # Delete old photo if exists
                if user.profile_photo:
                    delete_file(user.profile_photo)
                
                # Upload new photo
                object_path = generate_object_path(f"user_{user.id}", photo.filename)
                if upload_file(photo, object_path, photo.content_type):
                    user.profile_photo = object_path

    try:
        db.session.commit()

        # Log activity
        log = ActivityLog(
            user_id=user.id,
            action="PROFILE_UPDATED",
            resource_type="user",
            resource_id=user.id,
            ip_address=request.remote_addr,
            status="success"
        )
        db.session.add(log)
        db.session.commit()

        logger.info(f"User profile updated: {user.username}")

        return jsonify({
            "message": "Profile updated successfully",
            "user": user.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Profile update error: {e}")
        return jsonify({"error": "Update failed"}), 500


@users_bp.route("/users/me/password", methods=["PUT"])
@token_required
def change_password():
    """Change current user password"""
    current_user = request.current_user
    
    user = User.query.get(current_user["user_id"])
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Get password data
    current_password = request.form.get("current_password")
    new_password = request.form.get("new_password")
    confirm_password = request.form.get("confirm_password")
    
    if not all([current_password, new_password, confirm_password]):
        return jsonify({"error": "All password fields are required"}), 400
    
    # Verify current password
    if not verify_password(current_password, user.password_hash):
        return jsonify({"error": "Current password is incorrect"}), 401
    
    # Validate new password
    valid, msg = validate_password(new_password)
    if not valid:
        return jsonify({"error": msg}), 400
    
    # Check confirmation
    if new_password != confirm_password:
        return jsonify({"error": "New passwords do not match"}), 400
    
    # Update password
    user.password_hash = hash_password(new_password).decode("utf-8")
    
    try:
        db.session.commit()
        
        # Log activity
        log = ActivityLog(
            user_id=user.id,
            action="PASSWORD_CHANGED",
            resource_type="user",
            resource_id=user.id,
            ip_address=request.remote_addr,
            status="success"
        )
        db.session.add(log)
        db.session.commit()
        
        logger.info(f"Password changed for user: {user.username}")
        
        return jsonify({"message": "Password changed successfully"})
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Password change error: {e}")
        return jsonify({"error": "Password change failed"}), 500


@users_bp.route("/users/me/photo", methods=["PUT"])
@token_required
def update_profile_photo():
    """Update current user profile photo"""
    current_user = request.current_user
    
    user = User.query.get(current_user["user_id"])
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    if "profile_photo" not in request.files:
        return jsonify({"error": "No photo provided"}), 400
    
    photo = request.files["profile_photo"]
    
    if not photo.filename:
        return jsonify({"error": "Invalid file"}), 400
    
    # Validate image
    valid, msg = validate_image_file(photo, Config.ALLOWED_EXTENSIONS, Config.MAX_UPLOAD_SIZE)
    if not valid:
        return jsonify({"error": msg}), 400

    # Reset file pointer after validation
    photo.seek(0)

    try:
        # Delete old photo if exists
        if user.profile_photo:
            delete_file(user.profile_photo)

        # Upload new photo
        object_path = generate_object_path(user.id, photo.filename)
        if not upload_file(photo, object_path, photo.content_type):
            return jsonify({"error": "Upload failed"}), 500
        
        user.profile_photo = object_path
        db.session.commit()
        
        # Log activity
        log = ActivityLog(
            user_id=user.id,
            action="PROFILE_PHOTO_UPDATED",
            resource_type="user",
            resource_id=user.id,
            ip_address=request.remote_addr,
            status="success"
        )
        db.session.add(log)
        db.session.commit()
        
        logger.info(f"Profile photo updated for user: {user.username}")
        
        return jsonify({
            "message": "Profile photo updated",
            "photo_url": get_public_url(object_path) if object_path else None
        })
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Photo update error: {e}")
        return jsonify({"error": "Photo update failed"}), 500


@users_bp.route("/users/me/photo", methods=["DELETE"])
@token_required
def delete_profile_photo():
    """Delete current user profile photo"""
    current_user = request.current_user
    
    user = User.query.get(current_user["user_id"])
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    if not user.profile_photo:
        return jsonify({"error": "No profile photo to delete"}), 400
    
    try:
        # Delete from storage
        delete_file(user.profile_photo)
        
        user.profile_photo = None
        db.session.commit()
        
        # Log activity
        log = ActivityLog(
            user_id=user.id,
            action="PROFILE_PHOTO_DELETED",
            resource_type="user",
            resource_id=user.id,
            ip_address=request.remote_addr,
            status="success"
        )
        db.session.add(log)
        db.session.commit()
        
        logger.info(f"Profile photo deleted for user: {user.username}")
        
        return jsonify({"message": "Profile photo deleted"})
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Photo deletion error: {e}")
        return jsonify({"error": "Photo deletion failed"}), 500


@users_bp.route("/users/<int:user_id>", methods=["GET"])
@token_required
def get_user(user_id):
    """Get user by ID (public profile)"""
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    return jsonify({
        "user": {
            "id": user.id,
            "username": user.username,
            "profile_photo": user.profile_photo,
            "created_at": user.created_at.isoformat() if user.created_at else None
        }
    })
