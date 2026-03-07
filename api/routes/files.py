from flask import Blueprint, request, jsonify, send_file, current_app
from database import db
from models import User, File, SharedFile, ActivityLog, Notification
from services.auth_service import token_required, decode_token
from services.storage import (
    upload_file, delete_file, download_file, generate_object_path,
    get_public_url, file_exists
)
from utils.validator import validate_image_file, sanitize_filename
from utils.logger import get_logger
from config import Config
from sqlalchemy import or_
import uuid
from io import BytesIO
import os

files_bp = Blueprint("files", __name__)
logger = get_logger()


@files_bp.route("/image/<path:object_path>", methods=["GET"])
def serve_image(object_path):
    """Serve image from MinIO"""
    try:
        # Download file from MinIO
        file_data = download_file(object_path)
        
        if not file_data:
            return jsonify({"error": "File not found"}), 404
        
        # Determine content type from file extension
        ext = object_path.rsplit(".", 1)[-1].lower() if "." in object_path else ""
        content_types = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "gif": "image/gif",
            "webp": "image/webp",
            "bmp": "image/bmp"
        }
        content_type = content_types.get(ext, "image/jpeg")
        
        from flask import make_response
        response = make_response(file_data)
        response.headers['Content-Type'] = content_type
        response.headers['Cache-Control'] = 'no-cache'
        return response
        
    except Exception as e:
        logger.error(f"Error serving image: {e}")
        return jsonify({"error": "Failed to serve image"}), 500


def get_token_user_id():
    """Extract user ID from token"""
    token = None
    if "Authorization" in request.headers:
        auth_header = request.headers["Authorization"]
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
    
    if not token:
        return None
    
    payload = decode_token(token)
    return payload["user_id"] if payload else None


@files_bp.route("/upload", methods=["POST"])
@token_required
def upload():
    """Upload a new file"""
    current_user = request.current_user
    
    # Get file
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files["file"]
    
    if not file.filename:
        return jsonify({"error": "No file selected"}), 400
    
    # Get metadata
    filename = request.form.get("filename")
    category = request.form.get("category")
    visibility = request.form.get("visibility", "private")

    # Validate required fields
    if not filename:
        return jsonify({"error": "Filename is required"}), 400

    if not category:
        return jsonify({"error": "Category is required"}), 400

    # Validate visibility
    if visibility not in ["public", "private", "semipublic"]:
        return jsonify({"error": "Invalid visibility option"}), 400

    # Sanitize filename
    filename = sanitize_filename(filename)
    original_filename = sanitize_filename(file.filename)
    
    # If original filename has no extension, try to get it from content type
    if not original_filename or "." not in original_filename:
        # Try to determine extension from content type
        content_type = file.content_type or ""
        ext_map = {
            "image/jpeg": "jpg",
            "image/png": "png",
            "image/gif": "gif",
            "image/webp": "webp",
            "image/bmp": "bmp"
        }
        ext = ext_map.get(content_type, "jpg")
        original_filename = f"uploaded_file.{ext}" if not original_filename else f"{original_filename}.{ext}"
    
    # Get content type - auto-detect if not provided
    content_type = file.content_type
    if not content_type:
        # Try to guess from file extension
        import mimetypes
        ext = original_filename.rsplit(".", 1)[-1].lower() if "." in original_filename else ""
        content_type = mimetypes.guess_type(f"file.{ext}")[0] or "image/jpeg"
    
    # Validate file
    valid, msg = validate_image_file(file, Config.ALLOWED_EXTENSIONS, Config.MAX_UPLOAD_SIZE)
    if not valid:
        logger.error(f"File validation failed: {msg}")
        logger.error(f"File filename: {file.filename}")
        logger.error(f"File content_type: {file.content_type}")
        file.seek(0, 2)
        file_size = file.tell()
        file.seek(0)
        logger.error(f"File size: {file_size} bytes")
        return jsonify({"error": msg}), 400

    # Reset file pointer after validation
    file.seek(0)

    try:
        # Generate unique object path
        object_path = generate_object_path(current_user["user_id"], original_filename)

        # Upload to MinIO with correct content type
        if not upload_file(file, object_path, content_type):
            return jsonify({"error": "Upload failed"}), 500

        # Get file size
        file.seek(0, 2)
        file_size = file.tell()
        file.seek(0)

        # Generate share token for semipublic
        share_token = None
        if visibility == "semipublic":
            share_token = str(uuid.uuid4())

        # Create file record with mime_type
        new_file = File(
            filename=filename,
            original_filename=original_filename,
            category=category,
            file_size=file_size,
            mime_type=content_type,
            object_path=object_path,
            visibility=visibility,
            share_token=share_token,
            owner_id=current_user["user_id"]
        )
        
        db.session.add(new_file)
        db.session.commit()
        
        # Log activity
        log = ActivityLog(
            user_id=current_user["user_id"],
            action="FILE_UPLOADED",
            resource_type="file",
            resource_id=new_file.id,
            ip_address=request.remote_addr,
            details=f"Uploaded: {filename}",
            status="success"
        )
        db.session.add(log)
        db.session.commit()
        
        logger.info(f"File uploaded by {current_user['username']}: {filename}")
        
        return jsonify({
            "message": "File uploaded successfully",
            "file": new_file.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Upload error: {e}")
        return jsonify({"error": "Upload failed"}), 500


@files_bp.route("/my-files", methods=["GET"])
@token_required
def get_my_files():
    """Get current user's files"""
    current_user = request.current_user

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    category = request.args.get("category", "")
    visibility = request.args.get("visibility", "")

    query = File.query.filter_by(owner_id=current_user["user_id"])

    # Filters
    if category:
        query = query.filter_by(category=category)

    if visibility:
        query = query.filter_by(visibility=visibility)

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


@files_bp.route("/shared-with-me", methods=["GET"])
@token_required
def get_shared_with_me():
    """Get files shared with current user"""
    current_user = request.current_user

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    query_param = request.args.get("q", "")
    category = request.args.get("category", "")

    # Get files shared with this user - join with User table for owner info
    query = File.query.join(
        SharedFile, File.id == SharedFile.file_id
    ).join(
        User, File.owner_id == User.id
    ).filter(
        SharedFile.shared_with_user_id == current_user["user_id"]
    )

    # Apply search filter
    if query_param:
        query = query.filter(
            or_(
                File.filename.ilike(f"%{query_param}%"),
                File.original_filename.ilike(f"%{query_param}%"),
                File.category.ilike(f"%{query_param}%")
            )
        )

    # Apply category filter - use filter() instead of filter_by() after join
    if category:
        query = query.filter(File.category == category)

    # Order by shared_at desc
    query = query.order_by(SharedFile.shared_at.desc())

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


@files_bp.route("/<int:file_id>", methods=["GET"])
@token_required
def get_file(file_id):
    """Get file details - Owner only"""
    current_user = request.current_user

    file = File.query.get(file_id)

    if not file:
        return jsonify({"error": "File not found"}), 404

    # Check ownership - ONLY owner can access this endpoint
    if file.owner_id != current_user["user_id"]:
        return jsonify({"error": "Access denied. Use share link instead."}), 403

    return jsonify({"file": file.to_dict()})


@files_bp.route("/<int:file_id>", methods=["PUT"])
@token_required
def update_file(file_id):
    """Update file metadata"""
    current_user = request.current_user
    
    file = File.query.get(file_id)
    
    if not file:
        return jsonify({"error": "File not found"}), 404
    
    # Check ownership
    if file.owner_id != current_user["user_id"]:
        return jsonify({"error": "Access denied"}), 403
    
    # Get update data
    filename = request.form.get("filename")
    category = request.form.get("category")
    visibility = request.form.get("visibility")
    
    # Update fields
    if filename:
        file.filename = sanitize_filename(filename)
    
    if category:
        file.category = category
    
    if visibility:
        if visibility not in ["public", "private", "semipublic"]:
            return jsonify({"error": "Invalid visibility option"}), 400
        
        file.visibility = visibility
        
        # Generate new share token if changing to semipublic
        if visibility == "semipublic" and not file.share_token:
            file.share_token = str(uuid.uuid4())
        elif visibility != "semipublic":
            file.share_token = None
    
    try:
        db.session.commit()
        
        # Log activity
        log = ActivityLog(
            user_id=current_user["user_id"],
            action="FILE_UPDATED",
            resource_type="file",
            resource_id=file_id,
            ip_address=request.remote_addr,
            details=f"Updated: {file.filename}",
            status="success"
        )
        db.session.add(log)
        db.session.commit()
        
        logger.info(f"File updated by {current_user['username']}: {file.filename}")
        
        return jsonify({
            "message": "File updated successfully",
            "file": file.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"File update error: {e}")
        return jsonify({"error": "Update failed"}), 500


@files_bp.route("/<int:file_id>", methods=["DELETE"])
@token_required
def delete_file_endpoint(file_id):
    """Delete a file"""
    current_user = request.current_user
    
    file = File.query.get(file_id)
    
    if not file:
        return jsonify({"error": "File not found"}), 404
    
    # Check ownership
    if file.owner_id != current_user["user_id"]:
        return jsonify({"error": "Access denied"}), 403
    
    try:
        filename = file.filename
        
        # Delete from storage
        delete_file(file.object_path)
        
        # Delete record
        db.session.delete(file)
        db.session.commit()
        
        # Log activity
        log = ActivityLog(
            user_id=current_user["user_id"],
            action="FILE_DELETED",
            resource_type="file",
            resource_id=file_id,
            ip_address=request.remote_addr,
            details=f"Deleted: {filename}",
            status="success"
        )
        db.session.add(log)
        db.session.commit()
        
        logger.info(f"File deleted by {current_user['username']}: {filename}")
        
        return jsonify({"message": "File deleted successfully"})
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"File deletion error: {e}")
        return jsonify({"error": "Deletion failed"}), 500


@files_bp.route("/<int:file_id>/download", methods=["GET"])
@token_required
def download_file_endpoint(file_id):
    """Download a file"""
    current_user = request.current_user
    
    file = File.query.get(file_id)
    
    if not file:
        return jsonify({"error": "File not found"}), 404
    
    # Check access
    can_access = False

    if file.owner_id == current_user["user_id"]:
        can_access = True
    elif file.visibility == "public":
        can_access = True
    elif file.visibility == "semipublic":
        share = SharedFile.query.filter_by(
            file_id=file_id,
            shared_with_user_id=current_user["user_id"]
        ).first()
        if share:
            can_access = True

    if not can_access:
        return jsonify({"error": "Access denied"}), 403
    
    # Download from MinIO
    file_data = download_file(file.object_path)
    
    if not file_data:
        return jsonify({"error": "Download failed"}), 500
    
    # Update download count
    file.download_count += 1
    db.session.commit()
    
    # Log activity
    log = ActivityLog(
        user_id=current_user["user_id"],
        action="FILE_DOWNLOADED",
        resource_type="file",
        resource_id=file_id,
        ip_address=request.remote_addr,
        details=f"Downloaded: {file.filename}",
        status="success"
    )
    db.session.add(log)
    db.session.commit()
    
    logger.info(f"File downloaded by {current_user['username']}: {file.filename}")
    
    return send_file(
        BytesIO(file_data),
        mimetype=file.mime_type,
        as_attachment=True,
        download_name=file.original_filename
    )


@files_bp.route("/<int:file_id>/share", methods=["POST"])
@token_required
def share_file(file_id):
    """Share a semipublic file with another user"""
    current_user = request.current_user
    
    file = File.query.get(file_id)
    
    if not file:
        return jsonify({"error": "File not found"}), 404
    
    # Check ownership
    if file.owner_id != current_user["user_id"]:
        return jsonify({"error": "Access denied"}), 403
    
    # File must be semipublic
    if file.visibility != "semipublic":
        return jsonify({"error": "File must be semipublic to share"}), 400
    
    # Get target user
    target_username = request.form.get("username")
    
    if not target_username:
        return jsonify({"error": "Username required"}), 400

    target_user = User.query.filter_by(username=target_username).first()

    if not target_user:
        return jsonify({"error": "User not found"}), 404

    # Check if already shared
    existing = SharedFile.query.filter_by(
        file_id=file_id,
        shared_with_user_id=target_user.id
    ).first()

    if existing:
        return jsonify({"error": "Already shared with this user"}), 400

    try:
        # Create share record
        share = SharedFile(
            file_id=file_id,
            owner_id=current_user["user_id"],
            shared_with_user_id=target_user.id
        )

        db.session.add(share)

        # Create notification for the recipient with share token link
        notification = Notification(
            user_id=target_user.id,
            type="file_shared",
            title="File Shared with You",
            message=f"{current_user['username']} shared \"{file.filename}\" with you",
            link=f"/s/{file.share_token}"
        )
        db.session.add(notification)

        db.session.commit()

        # Log activity
        log = ActivityLog(
            user_id=current_user["user_id"],
            action="FILE_SHARED",
            resource_type="file",
            resource_id=file_id,
            ip_address=request.remote_addr,
            details=f"Shared {file.filename} with {target_username}",
            status="success"
        )
        db.session.add(log)
        db.session.commit()
        
        logger.info(f"File shared by {current_user['username']}: {file.filename} -> {target_username}")
        
        return jsonify({
            "message": "File shared successfully",
            "shared_with": target_user.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Share error: {e}")
        return jsonify({"error": "Share failed"}), 500


@files_bp.route("/shared/<share_token>", methods=["GET"])
def get_shared_file(share_token):
    """Get file by share token (public endpoint for sharing)"""
    file = File.query.filter_by(share_token=share_token).first()

    if not file:
        return jsonify({"error": "Invalid share link"}), 404

    if file.visibility != "semipublic":
        return jsonify({"error": "Invalid share link"}), 404

    return jsonify({"file": file.to_dict()})


@files_bp.route("/shared/<share_token>/download", methods=["GET"])
def download_shared_file(share_token):
    """Download file by share token (public endpoint for sharing)"""
    file = File.query.filter_by(share_token=share_token).first()

    if not file:
        return jsonify({"error": "Invalid share link"}), 404

    if file.visibility != "semipublic":
        return jsonify({"error": "Invalid share link"}), 404

    # Download from MinIO
    file_data = download_file(file.object_path)

    if not file_data:
        return jsonify({"error": "Download failed"}), 500

    # Update download count
    file.download_count += 1
    db.session.commit()

    # Log activity
    log = ActivityLog(
        user_id=file.owner_id,
        action="FILE_DOWNLOADED",
        resource_type="file",
        resource_id=file.id,
        ip_address=request.remote_addr,
        details=f"Downloaded via share link: {file.filename}",
        status="success"
    )
    db.session.add(log)
    db.session.commit()

    logger.info(f"File downloaded via share link: {file.filename}")

    return send_file(
        BytesIO(file_data),
        mimetype=file.mime_type,
        as_attachment=True,
        download_name=file.original_filename
    )


@files_bp.route("/categories", methods=["GET"])
@token_required
def get_categories():
    """Get list of categories used by current user"""
    current_user = request.current_user

    categories = db.session.query(File.category).filter_by(
        owner_id=current_user["user_id"]
    ).distinct().all()

    return jsonify({
        "categories": [c[0] for c in categories if c[0]]
    })


@files_bp.route("/notifications", methods=["GET"])
@token_required
def get_notifications():
    """Get current user's notifications"""
    current_user = request.current_user
    
    # Get unread count
    unread_count = Notification.query.filter_by(
        user_id=current_user["user_id"],
        is_read=False
    ).count()
    
    # Get recent notifications (last 20)
    notifications = Notification.query.filter_by(
        user_id=current_user["user_id"]
    ).order_by(Notification.created_at.desc()).limit(20).all()
    
    return jsonify({
        "notifications": [n.to_dict() for n in notifications],
        "unread_count": unread_count
    })


@files_bp.route("/notifications/mark-read", methods=["POST"])
@token_required
def mark_notifications_read():
    """Mark all notifications as read"""
    current_user = request.current_user
    
    Notification.query.filter_by(
        user_id=current_user["user_id"],
        is_read=False
    ).update({"is_read": True})
    
    db.session.commit()
    
    return jsonify({"message": "Notifications marked as read"})
