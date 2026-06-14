"""Users management router — sync version"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from admin.database import get_db
from admin.routers.auth import require_admin
from admin.schemas.auth import AdminUserInfo
from admin.schemas.user import UserInfo, UserListResponse
from admin.services.log_service import log_admin_action

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin/users", tags=["users"])


@router.get("", response_model=UserListResponse)
def get_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: AdminUserInfo = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get paginated list of all users"""
    result = db.execute(text("SELECT COUNT(*) FROM users"))
    total = result.scalar() or 0

    result = db.execute(
        text(
            "SELECT telegram_id, sp_id, username, full_name, balance, referrals, "
            "referred_by, language, COALESCE(is_blocked, false), created_at "
            "FROM users ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
        ),
        {"limit": page_size, "offset": (page - 1) * page_size},
    )
    rows = result.fetchall()

    users = [
        UserInfo(
            telegram_id=row[0], sp_id=row[1], username=row[2],
            full_name=row[3], balance=row[4], referrals=row[5] or 0,
            referred_by=row[6], language=row[7] or "uz",
            is_blocked=bool(row[8]) if row[8] is not None else False,
            created_at=str(row[9]) if row[9] else None,
        ) for row in rows
    ]

    return UserListResponse(total=total, page=page, page_size=page_size, users=users)


@router.get("/search", response_model=UserListResponse)
def search_users(
    query: str = Query(..., min_length=1),
    search_by: str = Query("telegram_id", pattern="^(telegram_id|username|sp_id)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: AdminUserInfo = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Search users by Telegram ID, username, or SP ID"""
    if search_by == "telegram_id":
        if not query.isdigit():
            raise HTTPException(status_code=400, detail="Telegram ID must be a number")
        where_clause = "WHERE u.telegram_id = :q"
        count_clause = "SELECT COUNT(*) FROM users u WHERE u.telegram_id = :q"
    elif search_by == "sp_id":
        if not query.isdigit():
            raise HTTPException(status_code=400, detail="SP ID must be a number")
        where_clause = "WHERE u.sp_id = :q"
        count_clause = "SELECT COUNT(*) FROM users u WHERE u.sp_id = :q"
    else:
        where_clause = "WHERE LOWER(u.username) LIKE LOWER(:q)"
        count_clause = "SELECT COUNT(*) FROM users u WHERE LOWER(u.username) LIKE LOWER(:q)"
        query = f"%{query}%"

    total_result = db.execute(text(count_clause), {"q": query})
    total = total_result.scalar() or 0

    sql = text(
        "SELECT u.telegram_id, u.sp_id, u.username, u.full_name, u.balance, "
        "u.referrals, u.referred_by, u.language, COALESCE(u.is_blocked, false), u.created_at "
        f"FROM users u {where_clause} ORDER BY u.created_at DESC "
        "LIMIT :limit OFFSET :offset"
    )
    result = db.execute(
        sql, {"q": query, "limit": page_size, "offset": (page - 1) * page_size},
    )
    rows = result.fetchall()

    users = [
        UserInfo(
            telegram_id=row[0], sp_id=row[1], username=row[2],
            full_name=row[3], balance=row[4], referrals=row[5] or 0,
            referred_by=row[6], language=row[7] or "uz",
            is_blocked=bool(row[8]) if row[8] is not None else False,
            created_at=str(row[9]) if row[9] else None,
        ) for row in rows
    ]

    return UserListResponse(total=total, page=page, page_size=page_size, users=users)


@router.get("/{telegram_id}", response_model=UserInfo)
def get_user(
    telegram_id: int,
    admin: AdminUserInfo = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get user by Telegram ID"""
    result = db.execute(
        text(
            "SELECT telegram_id, sp_id, username, full_name, balance, referrals, "
            "referred_by, language, COALESCE(is_blocked, false), created_at "
            "FROM users WHERE telegram_id = :tid"
        ),
        {"tid": telegram_id},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    return UserInfo(
        telegram_id=row[0], sp_id=row[1], username=row[2],
        full_name=row[3], balance=row[4], referrals=row[5] or 0,
        referred_by=row[6], language=row[7] or "uz",
        is_blocked=bool(row[8]) if row[8] is not None else False,
        created_at=str(row[9]) if row[9] else None,
    )


@router.post("/{telegram_id}/block")
def block_user(
    telegram_id: int,
    admin: AdminUserInfo = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Block a user"""
    result = db.execute(
        text("SELECT telegram_id FROM users WHERE telegram_id = :tid"),
        {"tid": telegram_id},
    )
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="User not found")

    db.execute(
        text("UPDATE users SET is_blocked = true WHERE telegram_id = :tid"),
        {"tid": telegram_id},
    )
    db.commit()

    log_admin_action(
        db, admin.id, admin.username, "user_block",
        entity_type="user", entity_id=str(telegram_id),
        details=f"User {telegram_id} blocked by admin {admin.username}",
    )

    return {"ok": True, "message": f"User {telegram_id} blocked"}


@router.post("/{telegram_id}/unblock")
def unblock_user(
    telegram_id: int,
    admin: AdminUserInfo = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Unblock a user"""
    result = db.execute(
        text("SELECT telegram_id FROM users WHERE telegram_id = :tid"),
        {"tid": telegram_id},
    )
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="User not found")

    db.execute(
        text("UPDATE users SET is_blocked = false WHERE telegram_id = :tid"),
        {"tid": telegram_id},
    )
    db.commit()

    log_admin_action(
        db, admin.id, admin.username, "user_unblock",
        entity_type="user", entity_id=str(telegram_id),
        details=f"User {telegram_id} unblocked by admin {admin.username}",
    )

    return {"ok": True, "message": f"User {telegram_id} unblocked"}


@router.delete("/{telegram_id}")
def delete_user(
    telegram_id: int,
    admin: AdminUserInfo = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Delete a user"""
    result = db.execute(
        text("SELECT telegram_id FROM users WHERE telegram_id = :tid"),
        {"tid": telegram_id},
    )
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="User not found")

    db.execute(text("DELETE FROM users WHERE telegram_id = :tid"), {"tid": telegram_id})
    db.commit()

    log_admin_action(
        db, admin.id, admin.username, "user_delete",
        entity_type="user", entity_id=str(telegram_id),
        details=f"User {telegram_id} deleted",
    )

    return {"ok": True, "message": "User deleted"}
