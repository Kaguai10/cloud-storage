from database import db
from datetime import datetime


class User(db.Model):

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True)
    email = db.Column(db.String, unique=True)
    password_hash = db.Column(db.String)
    profile_photo = db.Column(db.String)
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Convert user to dictionary"""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "profile_photo": f"/api/files/image/{self.profile_photo}" if self.profile_photo else None,
            "is_admin": self.is_admin,
            "is_active": self.is_active,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class File(db.Model):

    __tablename__ = "files"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String)
    original_filename = db.Column(db.String)
    object_path = db.Column(db.String)
    file_size = db.Column(db.Integer)
    mime_type = db.Column(db.String)
    category = db.Column(db.String)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    visibility = db.Column(db.String, default="private")
    # public | private | semipublic
    share_token = db.Column(db.String)
    download_count = db.Column(db.Integer, default=0)
    is_deleted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    owner = db.relationship("User", backref=db.backref("files", lazy=True))

    def to_dict(self):
        """Convert file to dictionary"""
        return {
            "id": self.id,
            "filename": self.filename,
            "original_filename": self.original_filename,
            "object_path": self.object_path,
            "file_size": self.file_size,
            "mime_type": self.mime_type,
            "category": self.category,
            "owner_id": self.owner_id,
            "owner": self.owner.to_dict() if self.owner else None,
            "visibility": self.visibility,
            "share_token": self.share_token,
            "download_count": self.download_count,
            "is_deleted": self.is_deleted,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class CaptchaSession(db.Model):
    """Model for storing captcha sessions"""

    __tablename__ = "captcha_sessions"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(32), unique=True, nullable=False)
    answer = db.Column(db.String(10), nullable=False)
    image_data = db.Column(db.Text)
    is_used = db.Column(db.Boolean, default=False)
    expires_at = db.Column(db.DateTime, nullable=False)

    def is_valid(self):
        """Check if captcha session is valid"""
        return not self.is_used and self.expires_at > datetime.utcnow()


class ActivityLog(db.Model):
    """Model for storing activity logs"""

    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    action = db.Column(db.String(100))
    resource_type = db.Column(db.String(50))
    resource_id = db.Column(db.Integer)
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(255))
    details = db.Column(db.Text)
    status = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Convert activity log to dictionary"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "details": self.details,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class SharedFile(db.Model):
    """Model for tracking shared files"""

    __tablename__ = "shared_files"

    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, nullable=False)
    owner_id = db.Column(db.Integer, nullable=False)
    shared_with_user_id = db.Column(db.Integer, nullable=False)
    shared_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Convert shared file to dictionary"""
        return {
            "id": self.id,
            "file_id": self.file_id,
            "owner_id": self.owner_id,
            "shared_with_user_id": self.shared_with_user_id,
            "shared_at": self.shared_at.isoformat() if self.shared_at else None
        }


class Notification(db.Model):
    """Model for storing user notifications"""

    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    type = db.Column(db.String(50), nullable=False)  # file_shared, file_downloaded, etc
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    link = db.Column(db.String(500))  # Optional link for notification
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Convert notification to dictionary"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "type": self.type,
            "title": self.title,
            "message": self.message,
            "link": self.link,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }