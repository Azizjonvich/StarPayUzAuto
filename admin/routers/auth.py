"""Authentication router — sync version"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from admin.database import get_db
from admin.schemas.auth import (
    AdminUserInfo,
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    TelegramAuthRequest,
)
from admin.services.auth_service import (
    authenticate_admin_by_credentials,
    authenticate_admin_by_telegram,
    get_admin_from_token,
    hash_password,
    verify_password,
)
from admin.services.log_service import log_admin_action

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin/auth", tags=["auth"])


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/login", response_model=LoginResponse)
def login(
    request: LoginRequest,
    req: Request,
    db: Session = Depends(get_db),
):
    """Login with username and password"""
    admin, token = authenticate_admin_by_credentials(
        db, request.username, request.password
    )
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=token or "Invalid credentials",
        )

    ip = get_client_ip(req)
    log_admin_action(
        db,
        admin.id,
        admin.username,
        "login",
        entity_type="auth",
        details=f"Login from IP: {ip}",
        ip_address=ip,
    )

    return LoginResponse(
        access_token=token,
        admin=AdminUserInfo(
            id=admin.id,
            username=admin.username,
            role=admin.role,
            telegram_id=admin.telegram_id,
        ),
    )


@router.post("/telegram", response_model=LoginResponse)
def telegram_login(
    request: TelegramAuthRequest,
    req: Request,
    db: Session = Depends(get_db),
):
    """Login via Telegram WebApp initData"""
    admin, token = authenticate_admin_by_telegram(db, request.init_data)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=token or "Authentication failed",
        )

    ip = get_client_ip(req)
    log_admin_action(
        db,
        admin.id,
        admin.username,
        "login",
        entity_type="auth",
        details=f"Telegram login from IP: {ip}",
        ip_address=ip,
    )

    return LoginResponse(
        access_token=token,
        admin=AdminUserInfo(
            id=admin.id,
            username=admin.username,
            role=admin.role,
            telegram_id=admin.telegram_id,
        ),
    )


@router.get("/me", response_model=AdminUserInfo)
def get_current_admin(
    request: Request,
    db: Session = Depends(get_db),
):
    """Get current admin info from Authorization header"""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    token = auth_header[7:]
    admin = get_admin_from_token(db, token)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    return AdminUserInfo(
        id=admin.id,
        username=admin.username,
        role=admin.role,
        telegram_id=admin.telegram_id,
    )


@router.post("/change-password")
def change_password(
    request: ChangePasswordRequest,
    req: Request,
    db: Session = Depends(get_db),
):
    """Change admin password"""
    auth_header = req.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    token = auth_header[7:]
    admin = get_admin_from_token(db, token)
    if not admin:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    if not verify_password(request.current_password, admin.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    if len(request.new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters")

    admin.password_hash = hash_password(request.new_password)
    db.commit()

    ip = get_client_ip(req)
    log_admin_action(
        db, admin.id, admin.username, "password_change",
        entity_type="auth", details="Password changed", ip_address=ip,
    )

    return {"ok": True, "message": "Password changed successfully"}


def require_admin(
    request: Request,
    db: Session = Depends(get_db),
) -> AdminUserInfo:
    """Dependency to require admin authentication"""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    token = auth_header[7:]
    admin = get_admin_from_token(db, token)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    return AdminUserInfo(
        id=admin.id,
        username=admin.username,
        role=admin.role,
        telegram_id=admin.telegram_id,
    )
