from flask import Blueprint, request, jsonify, current_app
from database import db
from models import User, ActivityLog
from utils.validator import validate_email, validate_username, validate_password
from services.auth_service import hash_password, verify_password, generate_token
from services.storage import upload_file, delete_file, generate_object_path
from utils.captcha import create_captcha_session, verify_captcha
from utils.logger import get_logger
from config import Config

auth_bp = Blueprint("auth", __name__)
logger = get_logger()


@auth_bp.route("/auth/captcha", methods=["GET"])
def get_captcha():
    """Generate a new captcha"""
    session_id, image_base64 = create_captcha_session()
    
    return jsonify({
        "session_id": session_id,
        "image": image_base64
    })


@auth_bp.route("/auth/register", methods=["POST"])
def register():
    """Register a new user"""
    # Get form data
    username = request.form.get("username")
    email = request.form.get("email")
    password = request.form.get("password")
    confirm_password = request.form.get("confirm_password")
    captcha_session_id = request.form.get("captcha_session_id")
    captcha_answer = request.form.get("captcha_answer")
    
    # Validate required fields
    if not all([username, email, password, confirm_password]):
        return jsonify({"error": "All fields are required"}), 400
    
    # Validate username
    valid, msg = validate_username(username)
    if not valid:
        return jsonify({"error": msg}), 400
    
    # Validate email
    if not validate_email(email):
        return jsonify({"error": "Invalid email format"}), 400
    
    # Validate password
    valid, msg = validate_password(password)
    if not valid:
        return jsonify({"error": msg}), 400
    
    # Check password confirmation
    if password != confirm_password:
        return jsonify({"error": "Passwords do not match"}), 400
    
    # Verify captcha
    if not captcha_session_id or not captcha_answer:
        return jsonify({"error": "Captcha verification required"}), 400

    if not verify_captcha(None, captcha_session_id, captcha_answer):
        return jsonify({"error": "Invalid captcha"}), 400

    # Check if username exists
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already taken"}), 400
    
    # Check if email exists
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 400
    
    # Hash password
    password_hash = hash_password(password).decode("utf-8")
    
    # Handle profile photo upload
    profile_photo_path = None
    if "profile_photo" in request.files:
        photo = request.files["profile_photo"]
        if photo.filename:
            from utils.validator import validate_image_file
            valid, msg = validate_image_file(photo, Config.ALLOWED_EXTENSIONS, Config.MAX_UPLOAD_SIZE)
            if valid:
                object_path = generate_object_path("temp", photo.filename)
                if upload_file(photo, object_path, photo.content_type):
                    profile_photo_path = object_path
    
    # Create user
    user = User(
        username=username,
        email=email,
        password_hash=password_hash,
        profile_photo=profile_photo_path,
        is_admin=False
    )
    
    try:
        db.session.add(user)
        db.session.commit()
        
        # Log activity
        log = ActivityLog(
            user_id=user.id,
            action="USER_REGISTERED",
            resource_type="user",
            resource_id=user.id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
            status="success"
        )
        db.session.add(log)
        db.session.commit()
        
        logger.info(f"New user registered: {username}")
        
        return jsonify({
            "message": "Registration successful",
            "user": user.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Registration error: {e}")
        return jsonify({"error": "Registration failed"}), 500


@auth_bp.route("/auth/login", methods=["POST"])
def login():
    """User login"""
    # Get form data
    username = request.form.get("username")
    password = request.form.get("password")
    captcha_session_id = request.form.get("captcha_session_id")
    captcha_answer = request.form.get("captcha_answer")
    
    # Validate required fields
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400
    
    # Verify captcha
    if not captcha_session_id or not captcha_answer:
        return jsonify({"error": "Captcha verification required"}), 400

    if not verify_captcha(None, captcha_session_id, captcha_answer):
        return jsonify({"error": "Invalid captcha"}), 400

    # Find user
    user = User.query.filter_by(username=username).first()
    
    if not user:
        # Log failed attempt
        log = ActivityLog(
            action="LOGIN_FAILED",
            resource_type="user",
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
            details=f"User not found: {username}",
            status="error"
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({"error": "Invalid credentials"}), 401
    
    if not user.is_active:
        return jsonify({"error": "Account is deactivated"}), 403
    
    # Verify password
    if not verify_password(password, user.password_hash):
        # Log failed attempt
        log = ActivityLog(
            user_id=user.id,
            action="LOGIN_FAILED",
            resource_type="user",
            resource_id=user.id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
            details="Invalid password",
            status="error"
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({"error": "Invalid credentials"}), 401
    
    # Generate token
    token = generate_token(user.id, user.username, user.is_admin)
    
    # Update last login
    from datetime import datetime
    user.last_login = datetime.utcnow()
    db.session.commit()
    
    # Log successful login
    log = ActivityLog(
        user_id=user.id,
        action="LOGIN_SUCCESS",
        resource_type="user",
        resource_id=user.id,
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent"),
        status="success"
    )
    db.session.add(log)
    db.session.commit()
    
    logger.info(f"User logged in: {username}")
    
    return jsonify({
        "message": "Login successful",
        "token": token,
        "user": user.to_dict()
    })
