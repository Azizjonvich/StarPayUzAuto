"""Authentication service — sync version"""
import hashlib
import hmac
import logging
from datetime import datetime, timedelta, timezone

import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from admin.config import (
    BOT_TOKEN,
    JWT_ALGORITHM,
    JWT_EXPIRATION_HOURS,
    JWT_SECRET_KEY,
)
from admin.models.admin_user import AdminUser

logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    """Simple SHA-256 password hashing with salt"""
    salt = JWT_SECRET_KEY[:16]
    return hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == password_hash


def create_access_token(admin_id: int, username: str, role: str) -> str:
    """Create JWT access token"""
    expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    payload = {
        "sub": str(admin_id),
        "username": username,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    """Decode and validate JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def validate_telegram_init_data(init_data: str) -> dict | None:
    """
    Validate Telegram WebApp initData signature.
    Returns the parsed data dict if valid, None otherwise.
    """
    try:
        import urllib.parse
        parsed = urllib.parse.parse_qs(init_data)
        data = {k: v[0] for k, v in parsed.items()}

        received_hash = data.pop("hash", None)
        if not received_hash:
            return None

        items = sorted(data.items())
        check_string = "\n".join(f"{k}={v}" for k, v in items)

        secret_key = hashlib.sha256(BOT_TOKEN.encode()).digest()
        expected_hash = hmac.new(
            secret_key, check_string.encode(), hashlib.sha256
        ).hexdigest()

        if hmac.compare_digest(expected_hash, received_hash):
            return data
        return None
    except Exception as e:
        logger.error(f"Telegram init data validation error: {e}")
        return None


def authenticate_admin_by_telegram(
    db: Session, init_data: str
) -> tuple[AdminUser | None, str | None]:
    """Authenticate admin via Telegram WebApp initData"""
    data = validate_telegram_init_data(init_data)
    if not data:
        return None, "Invalid init data"

    try:
        import json
        user_data = json.loads(data.get("user", "{}"))
        telegram_id = user_data.get("id")
    except (json.JSONDecodeError, KeyError, TypeError):
        return None, "Invalid user data in init data"

    if not telegram_id:
        return None, "No user ID in init data"

    result = db.execute(
        select(AdminUser).where(AdminUser.telegram_id == int(telegram_id))
    )
    admin = result.scalar_one_or_none()

    if not admin:
        return None, "Admin not found"
    if not admin.is_active:
        return None, "Admin account is disabled"

    admin.last_login_at = datetime.now(timezone.utc)
    db.commit()

    token = create_access_token(admin.id, admin.username, admin.role)
    return admin, token


def authenticate_admin_by_credentials(
    db: Session, username: str, password: str
) -> tuple[AdminUser | None, str | None]:
    """Authenticate admin by username/password"""
    result = db.execute(
        select(AdminUser).where(AdminUser.username == username)
    )
    admin = result.scalar_one_or_none()

    if not admin:
        return None, "Invalid credentials"
    if not admin.is_active:
        return None, "Account is disabled"
    if not verify_password(password, admin.password_hash):
        return None, "Invalid credentials"

    admin.last_login_at = datetime.now(timezone.utc)
    db.commit()

    token = create_access_token(admin.id, admin.username, admin.role)
    return admin, token


def get_admin_from_token(
    db: Session, token: str
) -> AdminUser | None:
    """Get admin user from JWT token"""
    payload = decode_access_token(token)
    if not payload:
        return None

    admin_id = int(payload.get("sub", 0))
    result = db.execute(
        select(AdminUser).where(
            AdminUser.id == admin_id,
            AdminUser.is_active == True,
        )
    )
    return result.scalar_one_or_none()
