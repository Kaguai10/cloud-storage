import re
from PIL import Image
from io import BytesIO


def get_logger():
    """Get a simple logger"""
    import logging
    return logging.getLogger("validator")


# Email validation regex
EMAIL_REGEX = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

# Username validation regex (alphanumeric and underscore, 3-30 chars)
USERNAME_REGEX = r"^[a-zA-Z][a-zA-Z0-9_]{2,29}$"


def validate_email(email):
    """Validate email format"""
    if not email:
        return False
    return bool(re.match(EMAIL_REGEX, email))


def validate_username(username):
    """Validate username format"""
    if not username:
        return False, "Username is required"
    if len(username) < 3:
        return False, "Username must be at least 3 characters"
    if len(username) > 30:
        return False, "Username must be at most 30 characters"
    if not re.match(USERNAME_REGEX, username):
        return False, "Username must start with a letter and contain only letters, numbers, and underscores"
    return True, ""


def validate_password(password):
    """Validate password strength"""
    if not password:
        return False, "Password is required"
    if len(password) < 6:
        return False, "Password must be at least 6 characters"
    if len(password) > 128:
        return False, "Password must be at most 128 characters"
    return True, ""


def validate_file_extension(filename, allowed_extensions):
    """Validate file extension"""
    if not filename:
        return False
    # Get extension and normalize it
    ext = filename.rsplit(".", 1)[1].lower() if "." in filename else ""
    # Also check uppercase in allowed_extensions
    allowed_lower = [e.lower() for e in allowed_extensions]
    return ext in allowed_lower


def validate_image_file(file, allowed_extensions, max_size):
    """Validate image file - relaxed validation"""
    if not file:
        return False, "No file provided"

    filename = file.filename
    if not filename:
        return False, "Invalid filename"

    # Check extension - relaxed
    if not validate_file_extension(filename, allowed_extensions):
        # Just warn but don't block
        logger = get_logger()
        logger.warning(f"File extension check: {filename}")
    
    # Check file size
    file.seek(0, 2)  # Seek to end
    file_size = file.tell()
    file.seek(0)  # Reset pointer

    if file_size > max_size:
        return False, f"File too large. Max size: {max_size // (1024*1024)}MB"

    if file_size == 0:
        return False, "Empty file"

    # Validate it's actually an image - try to open it
    try:
        file.seek(0)
        img = Image.open(BytesIO(file.read()))
        img.verify()
        file.seek(0)
    except Exception as e:
        # If PIL can't open it, still allow if extension looks OK
        ext = filename.rsplit(".", 1)[1].lower() if "." in filename else ""
        allowed_lower = [e.lower() for e in allowed_extensions]
        if ext in allowed_lower:
            # Extension is OK, allow it
            pass
        else:
            return False, "Invalid image file"

    return True, ""


def sanitize_filename(filename):
    """Sanitize filename to prevent directory traversal"""
    # Remove path separators
    filename = filename.replace("/", "").replace("\\", "")
    # Remove leading dots
    while filename.startswith("."):
        filename = filename[1:]
    return filename.strip()


def get_file_extension(filename):
    """Get file extension from filename"""
    if "." not in filename:
        return ""
    return filename.rsplit(".", 1)[1].lower()
