"""Audit log query endpoints strictly restricted to Administrator role."""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.api.deps import get_db, require_admin
from app.db.models import AuditLog, User

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs (Admin Only)"])


@router.get("/", response_model=List[dict])
async def get_audit_logs(
    actor_username: Optional[str] = Query(None, description="Filter by user username"),
    target_resource: Optional[str] = Query(None, description="Filter by resource"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """Retrieve immutable audit logs of all access to sensitive resources.

    Enforces strict role check: Accessible solely by users with 'admin' role.
    """
    stmt = select(AuditLog)
    if actor_username:
        stmt = stmt.where(AuditLog.actor_username == actor_username)
    if target_resource:
        stmt = stmt.where(AuditLog.target_resource == target_resource)

    stmt = stmt.order_by(desc(AuditLog.timestamp)).offset(offset).limit(limit)
    result = await db.execute(stmt)
    logs = result.scalars().all()
    return [log.to_dict() for log in logs]


@router.get("/stats")
async def get_audit_stats(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """Return aggregated audit statistics for executive security overview."""
    total_logs_q = await db.execute(select(func.count(AuditLog.id)))
    total_logs = total_logs_q.scalar() or 0

    return {
        "total_audit_records": total_logs,
    }
