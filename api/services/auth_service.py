import bcrypt
import jwt
from datetime import datetime, timedelta
from config import Config


def hash_password(password):
    """Hash password using bcrypt"""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt)


def verify_password(password, password_hash):
    """Verify password against hash"""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


def generate_token(user_id, username, is_admin=False):
    """Generate JWT token for user"""
    payload = {
        "user_id": user_id,
        "username": username,
        "is_admin": is_admin,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=Config.JWT_EXPIRATION_HOURS)
    }
    
    token = jwt.encode(payload, Config.JWT_SECRET, algorithm="HS256")
    return token


def decode_token(token):
    """Decode and verify JWT token"""
    try:
        payload = jwt.decode(token, Config.JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def token_required(f):
    """Decorator to require valid token for routes"""
    from functools import wraps
    from flask import request, jsonify
    
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Get token from header
        if "Authorization" in request.headers:
            auth_header = request.headers["Authorization"]
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
        
        if not token:
            return jsonify({"error": "Token is missing"}), 401
        
        payload = decode_token(token)
        if not payload:
            return jsonify({"error": "Token is invalid or expired"}), 401
        
        # Add user info to request context
        request.current_user = payload
        return f(*args, **kwargs)
    
    return decorated


def admin_required(f):
    """Decorator to require admin privileges"""
    from functools import wraps
    from flask import request, jsonify
    
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        if "Authorization" in request.headers:
            auth_header = request.headers["Authorization"]
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
        
        if not token:
            return jsonify({"error": "Token is missing"}), 401
        
        payload = decode_token(token)
        if not payload:
            return jsonify({"error": "Token is invalid or expired"}), 401
        
        if not payload.get("is_admin"):
            return jsonify({"error": "Admin access required"}), 403
        
        request.current_user = payload
        return f(*args, **kwargs)
    
    return decorated
