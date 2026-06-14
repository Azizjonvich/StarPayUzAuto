"""Balance management router — sync version"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from admin.database import get_db
from admin.routers.auth import require_admin
from admin.schemas.auth import AdminUserInfo
from admin.schemas.balance import (
    BalanceChangeRequest,
    BalanceDeductRequest,
    BalanceResetRequest,
    BalanceResponse,
    BalanceSetRequest,
    TransactionHistoryResponse,
    TransactionInfo,
)
from admin.services.log_service import log_admin_action

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin/balance", tags=["balance"])


def _get_user_balance(db: Session, telegram_id: int) -> int | None:
    result = db.execute(
        text("SELECT balance FROM users WHERE telegram_id = :tid"),
        {"tid": telegram_id},
    )
    row = result.fetchone()
    return row[0] if row else None


def _update_user_balance(db: Session, telegram_id: int, new_balance: int) -> bool:
    result = db.execute(
        text("UPDATE users SET balance = :bal WHERE telegram_id = :tid"),
        {"bal": new_balance, "tid": telegram_id},
    )
    db.commit()
    return result.rowcount > 0


def _record_transaction(
    db: Session,
    telegram_id: int,
    amount: int,
    tx_type: str,
    balance_before: int,
    balance_after: int,
    reason: str | None,
    admin_id: int,
):
    now = datetime.now(timezone.utc)
    db.execute(
        text(
            "INSERT INTO transactions (telegram_id, amount, type, balance_before, "
            "balance_after, reason, admin_id, created_at) "
            "VALUES (:tid, :amt, :typ, :bb, :ba, :reason, :aid, :now)"
        ),
        {
            "tid": telegram_id,
            "amt": amount,
            "typ": tx_type,
            "bb": balance_before,
            "ba": balance_after,
            "reason": reason or "",
            "aid": admin_id,
            "now": now,
        },
    )
    db.commit()


@router.post("/add")
def add_balance(
    request: BalanceChangeRequest,
    admin: AdminUserInfo = Depends(require_admin),
    db: Session = Depends(get_db),
):
    current_balance = _get_user_balance(db, request.telegram_id)
    if current_balance is None:
        raise HTTPException(status_code=404, detail="User not found")

    new_balance = current_balance + request.amount
    _update_user_balance(db, request.telegram_id, new_balance)
    _record_transaction(
        db, request.telegram_id, request.amount, "credit",
        current_balance, new_balance, request.reason, admin.id,
    )

    log_admin_action(
        db, admin.id, admin.username, "balance_change",
        entity_type="user", entity_id=str(request.telegram_id),
        details=f"Added {request.amount} to user {request.telegram_id}. Balance: {current_balance} -> {new_balance}. Reason: {request.reason or 'N/A'}",
    )

    return BalanceResponse(
        telegram_id=request.telegram_id,
        balance_before=current_balance,
        balance_after=new_balance,
        amount=request.amount,
        operation="add",
    )


@router.post("/deduct")
def deduct_balance(
    request: BalanceDeductRequest,
    admin: AdminUserInfo = Depends(require_admin),
    db: Session = Depends(get_db),
):
    current_balance = _get_user_balance(db, request.telegram_id)
    if current_balance is None:
        raise HTTPException(status_code=404, detail="User not found")
    if current_balance < request.amount:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient balance. Current: {current_balance}, Requested: {request.amount}",
        )

    new_balance = current_balance - request.amount
    _update_user_balance(db, request.telegram_id, new_balance)
    _record_transaction(
        db, request.telegram_id, request.amount, "debit",
        current_balance, new_balance, request.reason, admin.id,
    )

    log_admin_action(
        db, admin.id, admin.username, "balance_change",
        entity_type="user", entity_id=str(request.telegram_id),
        details=f"Deducted {request.amount} from user {request.telegram_id}. Balance: {current_balance} -> {new_balance}. Reason: {request.reason or 'N/A'}",
    )

    return BalanceResponse(
        telegram_id=request.telegram_id,
        balance_before=current_balance,
        balance_after=new_balance,
        amount=request.amount,
        operation="deduct",
    )


@router.post("/set")
def set_balance(
    request: BalanceSetRequest,
    admin: AdminUserInfo = Depends(require_admin),
    db: Session = Depends(get_db),
):
    current_balance = _get_user_balance(db, request.telegram_id)
    if current_balance is None:
        raise HTTPException(status_code=404, detail="User not found")

    _update_user_balance(db, request.telegram_id, request.amount)
    difference = request.amount - current_balance
    _record_transaction(
        db, request.telegram_id, abs(difference),
        "set" if difference >= 0 else "debit",
        current_balance, request.amount, request.reason, admin.id,
    )

    log_admin_action(
        db, admin.id, admin.username, "balance_change",
        entity_type="user", entity_id=str(request.telegram_id),
        details=f"Set balance to {request.amount} for user {request.telegram_id}. Previous: {current_balance}. Reason: {request.reason or 'N/A'}",
    )

    return BalanceResponse(
        telegram_id=request.telegram_id,
        balance_before=current_balance,
        balance_after=request.amount,
        amount=difference,
        operation="set",
    )


@router.post("/reset")
def reset_balance(
    request: BalanceResetRequest,
    admin: AdminUserInfo = Depends(require_admin),
    db: Session = Depends(get_db),
):
    current_balance = _get_user_balance(db, request.telegram_id)
    if current_balance is None:
        raise HTTPException(status_code=404, detail="User not found")

    _update_user_balance(db, request.telegram_id, 0)
    _record_transaction(
        db, request.telegram_id, current_balance, "reset",
        current_balance, 0, request.reason, admin.id,
    )

    log_admin_action(
        db, admin.id, admin.username, "balance_change",
        entity_type="user", entity_id=str(request.telegram_id),
        details=f"Reset balance to 0 for user {request.telegram_id}. Previous: {current_balance}. Reason: {request.reason or 'N/A'}",
    )

    return BalanceResponse(
        telegram_id=request.telegram_id,
        balance_before=current_balance,
        balance_after=0,
        amount=current_balance,
        operation="reset",
    )


@router.get("/history", response_model=TransactionHistoryResponse)
def get_balance_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    telegram_id: int | None = Query(None),
    admin: AdminUserInfo = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get balance change history"""
    # Check if table exists via try/except (SQLite compatible)
    try:
        if telegram_id:
            count_result = db.execute(
                text("SELECT COUNT(*) FROM transactions WHERE telegram_id = :tid"),
                {"tid": telegram_id},
            )
            total = count_result.scalar() or 0

            result = db.execute(
                text(
                    "SELECT id, telegram_id, amount, type, balance_before, balance_after, "
                    "reason, admin_id, created_at "
                    "FROM transactions WHERE telegram_id = :tid "
                    "ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
                ),
                {"tid": telegram_id, "limit": page_size, "offset": (page - 1) * page_size},
            )
        else:
            count_result = db.execute(text("SELECT COUNT(*) FROM transactions"))
            total = count_result.scalar() or 0

            result = db.execute(
                text(
                    "SELECT id, telegram_id, amount, type, balance_before, balance_after, "
                    "reason, admin_id, created_at "
                    "FROM transactions ORDER BY created_at DESC "
                    "LIMIT :limit OFFSET :offset"
                ),
                {"limit": page_size, "offset": (page - 1) * page_size},
            )

        rows = result.fetchall()
        transactions = [
            TransactionInfo(
                id=row[0], telegram_id=row[1], amount=row[2],
                type=row[3], balance_before=row[4], balance_after=row[5],
                reason=row[6], admin_id=row[7], created_at=str(row[8]) if row[8] else None,
            ) for row in rows
        ]
    except Exception:
        total = 0
        transactions = []

    return TransactionHistoryResponse(
        total=total, page=page, page_size=page_size, transactions=transactions
    )
