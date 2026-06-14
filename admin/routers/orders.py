"""Orders management router — sync version"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from admin.database import get_db
from admin.routers.auth import require_admin
from admin.schemas.auth import AdminUserInfo
from admin.schemas.user import OrderInfo, OrderListResponse, OrderStatusUpdate
from admin.services.log_service import log_admin_action

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin/orders", tags=["orders"])


@router.get("", response_model=OrderListResponse)
def get_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    product_type: str | None = Query(None),
    telegram_id: int | None = Query(None),
    admin: AdminUserInfo = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get paginated list of orders with optional filters"""
    where = []
    params = {}

    if status:
        where.append("o.status = :status")
        params["status"] = status
    if product_type:
        where.append("o.product_type = :ptype")
        params["ptype"] = product_type
    if telegram_id:
        where.append("o.telegram_id = :tid")
        params["tid"] = telegram_id

    where_sql = " WHERE " + " AND ".join(where) if where else ""

    try:
        count_result = db.execute(text(f"SELECT COUNT(*) FROM orders o{where_sql}"), params)
        total = count_result.scalar() or 0

        result = db.execute(
            text(
                "SELECT o.id, o.telegram_id, o.product_type, o.target_username, "
                "o.quantity, o.amount, o.status, o.external_id, o.created_at "
                f"FROM orders o{where_sql} ORDER BY o.id DESC "
                "LIMIT :limit OFFSET :offset"
            ),
            {**params, "limit": page_size, "offset": (page - 1) * page_size},
        )
        rows = result.fetchall()
    except Exception:
        total = 0
        rows = []

    orders = [
        OrderInfo(
            id=row[0], telegram_id=row[1], product_type=row[2],
            target_username=row[3], quantity=row[4], amount=row[5],
            status=row[6], external_id=row[7], created_at=str(row[8]) if row[8] else None,
        ) for row in rows
    ]

    return OrderListResponse(total=total, page=page, page_size=page_size, orders=orders)


@router.get("/{order_id}", response_model=OrderInfo)
def get_order(
    order_id: int,
    admin: AdminUserInfo = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get order details"""
    try:
        result = db.execute(
            text(
                "SELECT id, telegram_id, product_type, target_username, "
                "quantity, amount, status, external_id, created_at "
                "FROM orders WHERE id = :oid"
            ),
            {"oid": order_id},
        )
        row = result.fetchone()
    except Exception:
        row = None

    if not row:
        raise HTTPException(status_code=404, detail="Order not found")

    return OrderInfo(
        id=row[0], telegram_id=row[1], product_type=row[2],
        target_username=row[3], quantity=row[4], amount=row[5],
        status=row[6], external_id=row[7], created_at=str(row[8]) if row[8] else None,
    )


@router.put("/{order_id}/status")
def update_order_status(
    order_id: int,
    request: OrderStatusUpdate,
    admin: AdminUserInfo = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update order status"""
    try:
        result = db.execute(
            text("SELECT id, status, telegram_id, product_type FROM orders WHERE id = :oid"),
            {"oid": order_id},
        )
        row = result.fetchone()
    except Exception:
        row = None

    if not row:
        raise HTTPException(status_code=404, detail="Order not found")

    old_status = row[1]
    new_status = request.status
    valid_statuses = ["pending", "processing", "completed", "failed", "cancelled"]
    if new_status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}")

    db.execute(
        text("UPDATE orders SET status = :status WHERE id = :oid"),
        {"status": new_status, "oid": order_id},
    )
    db.commit()

    log_admin_action(
        db, admin.id, admin.username, "order_update",
        entity_type="order", entity_id=str(order_id),
        details=f"Order #{order_id} status changed: {old_status} -> {new_status} (user: {row[2]}, product: {row[3]})",
    )

    return {"ok": True, "message": f"Order #{order_id} status updated to {new_status}"}


@router.delete("/{order_id}")
def delete_order(
    order_id: int,
    admin: AdminUserInfo = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Delete an order"""
    try:
        result = db.execute(
            text("SELECT id FROM orders WHERE id = :oid"),
            {"oid": order_id},
        )
        existing = result.fetchone()
    except Exception:
        existing = None

    if not existing:
        raise HTTPException(status_code=404, detail="Order not found")

    db.execute(text("DELETE FROM orders WHERE id = :oid"), {"oid": order_id})
    db.commit()

    log_admin_action(
        db, admin.id, admin.username, "order_delete",
        entity_type="order", entity_id=str(order_id),
        details=f"Order #{order_id} deleted",
    )

    return {"ok": True, "message": f"Order #{order_id} deleted"}
