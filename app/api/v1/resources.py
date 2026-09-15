"""Endpoints for accessing sensitive enterprise resources."""
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config import settings
from app.core.rate_limiter import limiter
from app.api.deps import get_db, require_analyst_or_admin, require_admin
from app.db.models import Resource, User

router = APIRouter(prefix="/resources", tags=["Sensitive Resources"])


class ResourceCreate(BaseModel):
    resource_key: str
    name: str
    resource_type: str
    sensitivity_level: str
    is_sensitive: bool = True
    description: Optional[str] = None
    mock_data_payload: Optional[str] = None


@router.get("/", response_model=List[dict])
async def list_resources(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst_or_admin),
):
    """List available resources in catalog."""
    result = await db.execute(select(Resource).order_by(Resource.sensitivity_level.desc()))
    resources = result.scalars().all()
    return [r.to_dict() for r in resources]


@router.get("/{resource_key}")
@limiter.limit(settings.RATE_LIMIT_SENSITIVE)
async def access_resource(
    request: Request,
    resource_key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst_or_admin),
):
    """Query sensitive data from a specific resource.

    This request is automatically audited and streamed into the anomaly detection engine.
    """
    result = await db.execute(select(Resource).where(Resource.resource_key == resource_key))
    resource = result.scalar_one_or_none()

    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resource '{resource_key}' not found."
        )

    parsed_payload = None
    if resource.mock_data_payload:
        try:
            parsed_payload = json.loads(resource.mock_data_payload)
        except Exception:
            parsed_payload = resource.mock_data_payload

    return {
        "status": "success",
        "resource_key": resource.resource_key,
        "name": resource.name,
        "classification": resource.sensitivity_level,
        "resource_type": resource.resource_type,
        "accessed_by": current_user.username,
        "user_role": current_user.role,
        "data": parsed_payload,
    }


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_resource(
    resource_in: ResourceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Register a new sensitive resource (Admin role only)."""
    check = await db.execute(select(Resource).where(Resource.resource_key == resource_in.resource_key))
    if check.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Resource key '{resource_in.resource_key}' already exists."
        )

    res = Resource(
        resource_key=resource_in.resource_key.upper(),
        name=resource_in.name,
        resource_type=resource_in.resource_type.upper(),
        sensitivity_level=resource_in.sensitivity_level.upper(),
        is_sensitive=resource_in.is_sensitive,
        description=resource_in.description,
        mock_data_payload=resource_in.mock_data_payload,
    )
    db.add(res)
    await db.commit()
    await db.refresh(res)
    return res.to_dict()
