"""Anomaly querying, inspection, and resolution endpoints."""
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.api.deps import get_db, require_analyst_or_admin
from app.db.models import Anomaly, User

router = APIRouter(prefix="/anomalies", tags=["Anomalies"])


class ResolveAnomalyRequest(BaseModel):
    resolution_note: Optional[str] = "Investigated and verified legitimate access."


@router.get("/", response_model=List[dict])
async def list_anomalies(
    severity: Optional[str] = Query(None, description="Filter by severity: LOW, MEDIUM, HIGH, CRITICAL"),
    is_resolved: Optional[bool] = Query(None, description="Filter by resolution status"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst_or_admin),
):
    """List flagged anomalies.

    Admins see enterprise-wide anomalies. Analysts see team-wide or their own anomalies.
    """
    stmt = select(Anomaly)

    if current_user.role == "analyst":
        # Analysts see anomalies related to their user account
        stmt = stmt.where(Anomaly.username == current_user.username)

    if severity:
        stmt = stmt.where(Anomaly.severity == severity.upper())
    if is_resolved is not None:
        stmt = stmt.where(Anomaly.is_resolved == is_resolved)

    stmt = stmt.order_by(desc(Anomaly.timestamp)).limit(limit)
    result = await db.execute(stmt)
    anomalies = result.scalars().all()
    return [a.to_dict() for a in anomalies]


@router.get("/{anomaly_id}")
async def get_anomaly_detail(
    anomaly_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst_or_admin),
):
    """Retrieve in-depth mathematical or structural details of a specific anomaly."""
    result = await db.execute(select(Anomaly).where(Anomaly.id == anomaly_id))
    anomaly = result.scalar_one_or_none()

    if not anomaly:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Anomaly not found.")

    if current_user.role == "analyst" and anomaly.username != current_user.username:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this anomaly record.")

    return anomaly.to_dict()


@router.post("/{anomaly_id}/resolve")
async def resolve_anomaly(
    anomaly_id: int,
    body: ResolveAnomalyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst_or_admin),
):
    """Mark an anomaly as resolved with an optional investigator note."""
    result = await db.execute(select(Anomaly).where(Anomaly.id == anomaly_id))
    anomaly = result.scalar_one_or_none()

    if not anomaly:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Anomaly not found.")

    anomaly.is_resolved = True
    anomaly.resolved_by = current_user.username
    anomaly.resolved_at = datetime.now(timezone.utc)
    anomaly.resolution_note = body.resolution_note

    await db.commit()
    await db.refresh(anomaly)
    return anomaly.to_dict()
