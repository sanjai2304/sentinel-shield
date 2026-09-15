"""Common API route dependencies."""
from app.db.session import get_db
from app.core.rbac import (
    get_current_user,
    require_role,
    require_admin,
    require_analyst_or_admin,
)

__all__ = [
    "get_db",
    "get_current_user",
    "require_role",
    "require_admin",
    "require_analyst_or_admin",
]
