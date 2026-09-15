"""Pytest fixtures for testing SentinelShield."""
import asyncio
import os
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.db.base import Base
from app.db.session import get_db
from app.core.security import get_password_hash, create_access_token
from app.db.models import User, Resource
from app.main import app as fastapi_app
import app.db.session as db_session
import app.core.audit_middleware as audit_mod
import app.streaming.event_worker as worker_mod

# Use isolated in-memory or file-based SQLite test DB
TEST_DB_URL = "sqlite+aiosqlite:///./test_sentinel.db"

test_engine = create_async_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = async_sessionmaker(bind=test_engine, expire_on_commit=False)

db_session.async_session_factory = TestingSessionLocal
audit_mod.async_session_factory = TestingSessionLocal
worker_mod.async_session_factory = TestingSessionLocal


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def setup_test_database():
    """Recreate tables fresh before each test session."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Seed baseline users and resources
    async with TestingSessionLocal() as session:
        admin_user = User(
            username="admin",
            email="admin@test.io",
            hashed_password=get_password_hash("AdminSecret123!"),
            role="admin",
            department="Security",
            is_active=True,
        )
        analyst_user = User(
            username="analyst_bob",
            email="bob@test.io",
            hashed_password=get_password_hash("AnalystBob123!"),
            role="analyst",
            department="SOC",
            is_active=True,
        )
        resource_sensitive = Resource(
            resource_key="PII_CUSTOMER_VAULT",
            name="PII Customer Vault",
            resource_type="VAULT",
            sensitivity_level="RESTRICTED",
            is_sensitive=True,
            description="Sensitive Customer PII",
            mock_data_payload='{"identities": 1000}',
        )
        resource_normal = Resource(
            resource_key="INTERNAL_STAFF_DIR",
            name="Internal Staff Directory",
            resource_type="DIRECTORY",
            sensitivity_level="INTERNAL",
            is_sensitive=False,
            description="Staff directory",
            mock_data_payload='{"count": 50}',
        )
        session.add_all([admin_user, analyst_user, resource_sensitive, resource_normal])
        await session.commit()

    yield

    # Teardown
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    if os.path.exists("./test_sentinel.db"):
        try:
            os.remove("./test_sentinel.db")
        except Exception:
            pass


async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session


fastapi_app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def admin_token():
    return create_access_token(subject="admin", role="admin")


@pytest.fixture
def analyst_token():
    return create_access_token(subject="analyst_bob", role="analyst")


@pytest.fixture
async def async_client():
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
