from minio import Minio
from config import Config
from utils.logger import get_logger
import time

logger = get_logger()


def init_minio():
    """Initialize MinIO client with retry mechanism"""
    global minio_client
    
    max_retries = 30
    retry_delay = 2
    
    for attempt in range(1, max_retries + 1):
        try:
            client = Minio(
                Config.MINIO_ENDPOINT,
                access_key=Config.MINIO_ACCESS_KEY,
                secret_key=Config.MINIO_SECRET_KEY,
                secure=False
            )

            # Test connection
            client.bucket_exists(Config.MINIO_BUCKET)
            
            # Create bucket if not exists
            if not client.bucket_exists(Config.MINIO_BUCKET):
                client.make_bucket(Config.MINIO_BUCKET)
                logger.info(f"Bucket created: {Config.MINIO_BUCKET}")
            else:
                logger.info(f"Bucket exists: {Config.MINIO_BUCKET}")

            # Store client in config for later use
            from services.storage import set_minio_client
            set_minio_client(client)
            
            logger.info("MinIO initialized successfully")
            return client

        except Exception as e:
            if attempt < max_retries:
                logger.warning(f"MinIO not ready (attempt {attempt}/{max_retries}): {e}")
                time.sleep(retry_delay)
            else:
                logger.error(f"MinIO init failed after {max_retries} attempts: {e}")
                raise
    
    return None
