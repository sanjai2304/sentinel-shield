"""Database schema initialization and seed data generation."""
import json
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.base import Base
from app.db.session import engine, async_session_factory
from app.db.models import User, Resource
from app.core.security import get_password_hash

logger = logging.getLogger("sentinel.db")


INITIAL_USERS = [
    {
        "username": "admin",
        "email": "admin@sentinelshield.io",
        "password": "AdminSecret123!",
        "role": "admin",
        "department": "Security Leadership",
    },
    {
        "username": "analyst_alice",
        "email": "alice@sentinelshield.io",
        "password": "AnalystAlice123!",
        "role": "analyst",
        "department": "Threat Intelligence",
    },
    {
        "username": "analyst_bob",
        "email": "bob@sentinelshield.io",
        "password": "AnalystBob123!",
        "role": "analyst",
        "department": "Data Compliance",
    },
    {
        "username": "analyst_carol",
        "email": "carol@sentinelshield.io",
        "password": "AnalystCarol123!",
        "role": "analyst",
        "department": "Incident Response",
    },
]

INITIAL_RESOURCES = [
    {
        "resource_key": "INTERNAL_STAFF_DIR",
        "name": "Internal Staff Directory",
        "resource_type": "DIRECTORY",
        "sensitivity_level": "INTERNAL",
        "is_sensitive": False,
        "description": "Standard company directory containing employee names, emails, and office locations.",
        "mock_data_payload": json.dumps({"records_count": 450, "classification": "INTERNAL", "exportable": False}),
    },
    {
        "resource_key": "CUSTOMER_CRM_DB",
        "name": "Customer Relationship Database",
        "resource_type": "DATABASE",
        "sensitivity_level": "CONFIDENTIAL",
        "is_sensitive": True,
        "description": "Customer contacts, interaction histories, subscription levels, and account notes.",
        "mock_data_payload": json.dumps({"active_accounts": 12800, "masked_fields": ["phone", "email"]}),
    },
    {
        "resource_key": "FINANCIAL_LEDGER_Q3",
        "name": "Quarterly Financial General Ledger",
        "resource_type": "LEDGER",
        "sensitivity_level": "RESTRICTED",
        "is_sensitive": True,
        "description": "Sensitive corporate accounting transactions, accounts payable, and revenue ledgers.",
        "mock_data_payload": json.dumps({"fiscal_quarter": "Q3-2026", "journal_entries": 4320}),
    },
    {
        "resource_key": "PII_CUSTOMER_VAULT",
        "name": "PII & Identity Vault",
        "resource_type": "VAULT",
        "sensitivity_level": "RESTRICTED",
        "is_sensitive": True,
        "description": "Government IDs, SSNs, and biometric identity hashes for registered users.",
        "mock_data_payload": json.dumps({"algorithm": "AES-256-GCM", "protected_identities": 84200}),
    },
    {
        "resource_key": "PAYROLL_SALARY_DATA",
        "name": "Corporate Payroll & Compensation Table",
        "resource_type": "DATABASE",
        "sensitivity_level": "RESTRICTED",
        "is_sensitive": True,
        "description": "Executive and staff salary tiers, equity allocations, and bank routing numbers.",
        "mock_data_payload": json.dumps({"currency": "USD", "payroll_cycles": 24}),
    },
    {
        "resource_key": "EXECUTIVE_BOARD_MINUTES",
        "name": "Executive Board Strategy Documents",
        "resource_type": "DOCUMENT_STORE",
        "sensitivity_level": "RESTRICTED",
        "is_sensitive": True,
        "description": "Confidential merger, acquisition, and strategic roadmap meeting recordings.",
        "mock_data_payload": json.dumps({"documents": ["2026_M&A_Strategy.pdf", "Board_Minutes_Sept.pdf"]}),
    },
    {
        "resource_key": "SYSTEM_ROOT_CREDENTIALS",
        "name": "Cloud Infrastructure Master Key Vault",
        "resource_type": "KEY_VAULT",
        "sensitivity_level": "TOP_SECRET",
        "is_sensitive": True,
        "description": "Hardware security module master signing keys and cloud root credentials.",
        "mock_data_payload": json.dumps({"vault_engine": "Vault-HSM-v2", "keys_active": 18}),
    },
    {
        "resource_key": "PCI_PAYMENT_TOKENS",
        "name": "PCI-DSS Payment Token Gateway",
        "resource_type": "PAYMENT_GATEWAY",
        "sensitivity_level": "TOP_SECRET",
        "is_sensitive": True,
        "description": "Decryption endpoint for primary account numbers and card security tokens.",
        "mock_data_payload": json.dumps({"gateway_status": "LOCKED", "token_volume_today": 9431}),
    },
]


async def init_db() -> None:
    """Create all database tables and seed baseline users and resources."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        # Check if users already seeded
        result = await session.execute(select(User).limit(1))
        existing_user = result.scalar_one_or_none()

        if not existing_user:
            logger.info("Seeding initial users...")
            for u in INITIAL_USERS:
                user = User(
                    username=u["username"],
                    email=u["email"],
                    hashed_password=get_password_hash(u["password"]),
                    role=u["role"],
                    department=u["department"],
                    is_active=True,
                )
                session.add(user)
            await session.commit()

        # Check if resources already seeded
        res_check = await session.execute(select(Resource).limit(1))
        existing_res = res_check.scalar_one_or_none()

        if not existing_res:
            logger.info("Seeding initial resources...")
            for r in INITIAL_RESOURCES:
                res = Resource(
                    resource_key=r["resource_key"],
                    name=r["name"],
                    resource_type=r["resource_type"],
                    sensitivity_level=r["sensitivity_level"],
                    is_sensitive=r["is_sensitive"],
                    description=r["description"],
                    mock_data_payload=r["mock_data_payload"],
                )
                session.add(res)
            await session.commit()
            logger.info("Database initialized and seeded successfully.")
