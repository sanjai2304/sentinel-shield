"""Integration tests verifying Role-Based Access Control (RBAC) enforcement."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_unauthenticated_request_rejected(async_client: AsyncClient):
    """Endpoints requiring authentication must reject unauthenticated requests with 401."""
    response = await async_client.get("/api/v1/resources/")
    assert response.status_code == 401
    assert "detail" in response.json()


@pytest.mark.asyncio
async def test_analyst_can_access_resources(async_client: AsyncClient, analyst_token: str):
    """Users with 'analyst' role must be permitted to list and query sensitive resources."""
    headers = {"Authorization": f"Bearer {analyst_token}"}
    response = await async_client.get("/api/v1/resources/", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1

    # Access specific sensitive resource
    detail_res = await async_client.get("/api/v1/resources/PII_CUSTOMER_VAULT", headers=headers)
    assert detail_res.status_code == 200
    assert detail_res.json()["resource_key"] == "PII_CUSTOMER_VAULT"


@pytest.mark.asyncio
async def test_analyst_forbidden_from_audit_logs(async_client: AsyncClient, analyst_token: str):
    """Users with 'analyst' role must be strictly forbidden (403) from querying audit logs."""
    headers = {"Authorization": f"Bearer {analyst_token}"}
    response = await async_client.get("/api/v1/audit-logs/", headers=headers)
    assert response.status_code == 403
    assert "Access denied" in response.json()["detail"]


@pytest.mark.asyncio
async def test_admin_permitted_to_audit_logs(async_client: AsyncClient, admin_token: str):
    """Users with 'admin' role must be permitted (200) to query system audit logs."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = await async_client.get("/api/v1/audit-logs/", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_admin_only_resource_creation(async_client: AsyncClient, analyst_token: str, admin_token: str):
    """Only admins can create resources; analysts must receive 403."""
    payload = {
        "resource_key": "NEW_SENSITIVE_LEDGER",
        "name": "New Sensitive Ledger",
        "resource_type": "LEDGER",
        "sensitivity_level": "RESTRICTED",
        "is_sensitive": True,
    }

    # 1. Analyst attempts creation -> 403 Forbidden
    analyst_headers = {"Authorization": f"Bearer {analyst_token}"}
    analyst_res = await async_client.post("/api/v1/resources/", json=payload, headers=analyst_headers)
    assert analyst_res.status_code == 403

    # 2. Admin attempts creation -> 201 Created
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    admin_res = await async_client.post("/api/v1/resources/", json=payload, headers=admin_headers)
    assert admin_res.status_code == 201
    assert admin_res.json()["resource_key"] == "NEW_SENSITIVE_LEDGER"
