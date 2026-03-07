import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime


logger = None


def setup_logger(app):
    """Setup application logger with file and console handlers"""
    global logger
    
    log_level = getattr(logging, app.config.get("LOG_LEVEL", "INFO").upper())
    log_dir = app.config.get("LOG_DIR", "/app/logs")
    
    # Create logs directory
    os.makedirs(log_dir, exist_ok=True)
    
    logger = logging.getLogger(app.name)
    logger.setLevel(log_level)
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, f"api_{datetime.now().strftime('%Y%m%d')}.log"),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=10
    )
    file_handler.setLevel(log_level)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    
    # Formatter
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


def get_logger():
    """Get the application logger"""
    global logger
    if logger is None:
        logger = logging.getLogger("api")
        if not logger.handlers:
            logging.basicConfig(
                level=logging.INFO,
                format="%(asctime)s [%(levelname)s] %(message)s"
            )
    return logger
