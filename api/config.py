import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration class"""
    
    # Flask
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    DEBUG = os.getenv("FLASK_ENV", "development") == "development"
    
    # Database
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        f"postgresql://{os.getenv('POSTGRES_USER', 'clouduserdb')}:{os.getenv('POSTGRES_PASSWORD', 'cloudpassdb')}@{os.getenv('POSTGRES_HOST', 'db')}:{os.getenv('POSTGRES_PORT', '5432')}/{os.getenv('POSTGRES_DB', 'clouddb')}"
    )
    
    # MinIO
    MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
    MINIO_PUBLIC_ENDPOINT = os.getenv("MINIO_PUBLIC_ENDPOINT", "localhost:9000")
    # MinIO uses MINIO_ROOT_USER/MINIO_ROOT_PASSWORD (new vars) or MINIO_ACCESS_KEY/MINIO_SECRET_KEY (legacy)
    MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", os.getenv("MINIO_ROOT_USER", "adminminio"))
    MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", os.getenv("MINIO_ROOT_PASSWORD", "MinioSecret2026!"))
    MINIO_BUCKET = os.getenv("MINIO_BUCKET", "cloud-storage")
    
    # JWT
    JWT_SECRET = os.getenv("JWT_SECRET", "jwt-secret-key")
    JWT_EXPIRATION_HOURS = 6
    
    # Upload limits
    MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", 52428800))  # 50MB default
    
    # Allowed file extensions
    ALLOWED_EXTENSIONS = set(os.getenv("ALLOWED_EXTENSIONS", "png,jpg,jpeg,gif,webp,bmp").split(","))
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_DIR = os.getenv("LOG_DIR", "/app/logs")
