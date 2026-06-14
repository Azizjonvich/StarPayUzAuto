"""Admin activity logging service — sync version"""
import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from admin.models.log import AdminLog

logger = logging.getLogger(__name__)


def log_admin_action(
    db: Session,
    admin_id: int,
    admin_username: str,
    action: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    details: str | None = None,
    ip_address: str | None = None,
) -> AdminLog:
    """Log an admin action"""
    log_entry = AdminLog(
        admin_id=admin_id,
        admin_username=admin_username,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
        ip_address=ip_address,
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    logger.info(f"Admin action: {action} by {admin_username} - {details}")
    return log_entry


def get_logs(
    db: Session,
    page: int = 1,
    page_size: int = 50,
    action: str | None = None,
    admin_id: int | None = None,
) -> tuple[list[AdminLog], int]:
    """Get paginated logs"""
    query = select(AdminLog)
    count_query = select(func.count(AdminLog.id))

    if action:
        query = query.where(AdminLog.action == action)
        count_query = count_query.where(AdminLog.action == action)
    if admin_id:
        query = query.where(AdminLog.admin_id == admin_id)
        count_query = count_query.where(AdminLog.admin_id == admin_id)

    total_result = db.execute(count_query)
    total = total_result.scalar() or 0

    query = (
        query
        .order_by(AdminLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = db.execute(query)
    logs = list(result.scalars().all())

    return logs, total
