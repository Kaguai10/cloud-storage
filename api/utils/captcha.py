import random
import string
import base64
import os
from io import BytesIO
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from database import db
from models import CaptchaSession


def generate_captcha_text(length=5):
    """Generate random captcha text"""
    chars = string.ascii_uppercase + string.digits
    # Remove confusing characters
    chars = chars.replace("O", "").replace("0", "").replace("I", "").replace("1", "")
    return "".join(random.choice(chars) for _ in range(length))


def create_captcha_image(text, width=200, height=80):
    """Create captcha image with noise"""
    # Create image with random background color
    bg_color = (random.randint(200, 255), random.randint(200, 255), random.randint(200, 255))
    image = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(image)
    
    # Try to load a font, fall back to default if not available
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
    except:
        try:
            font = ImageFont.truetype("/usr/share/fonts/TTF/DejaVuSans-Bold.ttf", 36)
        except:
            font = ImageFont.load_default()
    
    # Add noise lines
    for _ in range(random.randint(3, 6)):
        start = (random.randint(0, width), random.randint(0, height))
        end = (random.randint(0, width), random.randint(0, height))
        line_color = (
            random.randint(100, 200),
            random.randint(100, 200),
            random.randint(100, 200)
        )
        draw.line([start, end], fill=line_color, width=2)
    
    # Add noise dots
    for _ in range(random.randint(100, 200)):
        point = (random.randint(0, width), random.randint(0, height))
        dot_color = (
            random.randint(100, 200),
            random.randint(100, 200),
            random.randint(100, 200)
        )
        draw.point(point, fill=dot_color)
    
    # Draw text with random colors and slight position variations
    char_width = width // (len(text) + 1)
    for i, char in enumerate(text):
        char_color = (
            random.randint(0, 100),
            random.randint(0, 100),
            random.randint(0, 100)
        )
        x = char_width * (i + 1) - 10
        y = random.randint(15, 35)
        draw.text((x, y), char, font=font, fill=char_color)
    
    # Apply slight blur
    image = image.filter(ImageFilter.GaussianBlur(radius=1))
    
    return image


def generate_captcha_image_base64():
    """Generate captcha and return as base64 string"""
    text = generate_captcha_text()
    image = create_captcha_image(text)
    
    # Convert to base64
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    return text, image_base64


def create_captcha_session(app=None):
    """Create a new captcha session"""
    from flask import current_app
    
    session_id = "".join(random.choices(string.ascii_letters + string.digits, k=32))
    answer, image_base64 = generate_captcha_image_base64()
    
    captcha = CaptchaSession(
        session_id=session_id,
        answer=answer.upper(),
        image_data=image_base64,
        expires_at=datetime.utcnow() + timedelta(minutes=5)
    )
    
    # Use current_app if app not provided
    if app is None:
        from database import db
        db.session.add(captcha)
        db.session.commit()
    else:
        with app.app_context():
            from database import db
            db.session.add(captcha)
            db.session.commit()
    
    return session_id, image_base64


def verify_captcha(app, session_id, user_answer):
    """Verify captcha answer"""
    from database import db
    
    captcha = CaptchaSession.query.filter_by(session_id=session_id).first()
    
    if not captcha:
        return False
    
    if not captcha.is_valid():
        # Mark as used even if expired
        captcha.is_used = True
        db.session.commit()
        return False
    
    if user_answer.upper() == captcha.answer:
        captcha.is_used = True
        db.session.commit()
        return True
    
    return False


def cleanup_expired_captchas():
    """Remove expired captcha sessions"""
    try:
        expired = CaptchaSession.query.filter(
            CaptchaSession.expires_at < datetime.utcnow()
        ).all()

        for c in expired:
            db.session.delete(c)

        db.session.commit()
    except Exception as e:
        # Ignore errors during cleanup (table might not exist yet)
        pass


def init_captcha_db(app=None):
    """Initialize captcha cleanup"""
    cleanup_expired_captchas()
