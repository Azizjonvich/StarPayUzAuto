"""Logs router — sync version"""
import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from admin.database import get_db
from admin.routers.auth import require_admin
from admin.schemas.auth import AdminUserInfo
from admin.schemas.log import LogInfo, LogListResponse
from admin.services.log_service import get_logs

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin/logs", tags=["logs"])


@router.get("", response_model=LogListResponse)
def get_admin_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    action: str | None = Query(None),
    admin_id: int | None = Query(None),
    current_admin: AdminUserInfo = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get admin activity logs"""
    logs, total = get_logs(
        db, page=page, page_size=page_size, action=action, admin_id=admin_id
    )

    return LogListResponse(
        total=total,
        page=page,
        page_size=page_size,
        logs=[
            LogInfo(
                id=log.id, admin_id=log.admin_id,
                admin_username=log.admin_username, action=log.action,
                entity_type=log.entity_type, entity_id=log.entity_id,
                details=log.details, ip_address=log.ip_address,
                created_at=log.created_at,
            )
            for log in logs
        ],
    )
