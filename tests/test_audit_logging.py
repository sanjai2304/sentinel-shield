"""Tests verifying the sensitive resource audit logging middleware."""
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from tests.conftest import TestingSessionLocal
from app.db.models import AuditLog


@pytest.mark.asyncio
async def test_access_to_sensitive_resource_is_audited(async_client: AsyncClient, analyst_token: str):
    """Every access to a sensitive resource must produce an immutable audit log record."""
    headers = {"Authorization": f"Bearer {analyst_token}"}
    
    # Perform read on sensitive vault
    response = await async_client.get("/api/v1/resources/PII_CUSTOMER_VAULT", headers=headers)
    assert response.status_code == 200

    # Query audit logs from test database
    async with TestingSessionLocal() as session:
        result = await session.execute(
            select(AuditLog).where(AuditLog.target_resource == "PII_CUSTOMER_VAULT")
        )
        logs = result.scalars().all()

        assert len(logs) >= 1, "Audit log record must be created for sensitive access"
        latest = logs[-1]
        assert latest.actor_username == "analyst_bob"
        assert latest.target_resource == "PII_CUSTOMER_VAULT"
        assert latest.action == "READ"
        assert latest.response_status == 200
        assert latest.route_path == "/api/v1/resources/PII_CUSTOMER_VAULT"
