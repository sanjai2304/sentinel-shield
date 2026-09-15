"""Tests verifying rate limiting behavior on public endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_auth_rate_limiting(async_client: AsyncClient):
    """Exceeding the rate limit on login must return HTTP 429."""
    login_payload = {"username": "admin", "password": "wrongpassword"}

    responses = []
    # Send 25 rapid requests (rate limit is 20/minute)
    for _ in range(25):
        res = await async_client.post("/api/v1/auth/login", json=login_payload)
        responses.append(res.status_code)

    # At least one request should be 429
    assert 429 in responses, f"Expected 429 status code in responses, got: {responses}"
