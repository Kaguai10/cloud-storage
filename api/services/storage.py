import uuid
from datetime import timedelta
from minio import Minio
from minio.error import S3Error
from config import Config
from utils.logger import get_logger


logger = get_logger()

# Global MinIO client
_minio_client = None


def set_minio_client(client):
    """Set the global MinIO client"""
    global _minio_client
    _minio_client = client


def get_minio_client():
    """Create or return existing MinIO client"""
    global _minio_client

    if _minio_client:
        return _minio_client

    try:
        _minio_client = Minio(
            Config.MINIO_ENDPOINT,
            access_key=Config.MINIO_ACCESS_KEY,
            secret_key=Config.MINIO_SECRET_KEY,
            secure=False
        )

        # Ensure bucket exists
        if not _minio_client.bucket_exists(Config.MINIO_BUCKET):
            _minio_client.make_bucket(Config.MINIO_BUCKET)
            logger.info(f"Created bucket: {Config.MINIO_BUCKET}")

        return _minio_client

    except Exception as e:
        logger.error(f"MinIO client initialization failed: {e}")
        raise


def upload_file(file, object_path, content_type="application/octet-stream"):
    """Upload file to MinIO"""

    try:
        client = get_minio_client()

        file.seek(0, 2)
        file_size = file.tell()
        file.seek(0)

        client.put_object(
            bucket_name=Config.MINIO_BUCKET,
            object_name=object_path,
            data=file,
            length=file_size,
            content_type=content_type
        )

        logger.info(f"File uploaded successfully: {object_path}")
        return object_path

    except S3Error as e:
        logger.error(f"MinIO upload error: {e}")
        return None
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return None


def download_file(object_path):
    """Download file from MinIO"""

    try:
        client = get_minio_client()

        response = client.get_object(Config.MINIO_BUCKET, object_path)
        data = response.read()

        response.close()
        response.release_conn()

        logger.info(f"File downloaded successfully: {object_path}")
        return data

    except S3Error as e:
        logger.error(f"MinIO download error: {e}")
        return None
    except Exception as e:
        logger.error(f"Download error: {e}")
        return None


def delete_file(object_path):
    """Delete file from MinIO"""

    try:
        client = get_minio_client()

        client.remove_object(Config.MINIO_BUCKET, object_path)

        logger.info(f"File deleted successfully: {object_path}")
        return True

    except S3Error as e:
        logger.error(f"MinIO delete error: {e}")
        return False
    except Exception as e:
        logger.error(f"Delete error: {e}")
        return False


def file_exists(object_path):
    """Check if file exists"""

    try:
        client = get_minio_client()
        client.stat_object(Config.MINIO_BUCKET, object_path)
        return True

    except S3Error:
        return False
    except Exception:
        return False


def get_presigned_url(object_path, expires=3600):
    """Generate temporary access URL"""

    try:
        client = get_minio_client()

        url = client.presigned_get_object(
            Config.MINIO_BUCKET,
            object_path,
            expires=timedelta(seconds=expires)
        )

        return url

    except Exception as e:
        logger.error(f"Presigned URL error: {e}")
        return None


def generate_object_path(user_id, filename):
    """Generate unique object path"""

    unique_id = str(uuid.uuid4())

    ext = "bin"
    if "." in filename:
        ext = filename.rsplit(".", 1)[1].lower()

    return f"user_{user_id}/{unique_id}.{ext}"


def get_public_url(object_path):
    return f"http://{Config.MINIO_PUBLIC_ENDPOINT}/{Config.MINIO_BUCKET}/{object_path}"
