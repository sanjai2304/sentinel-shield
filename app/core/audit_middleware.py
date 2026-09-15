"""Audit logging middleware for intercepting and logging sensitive data access."""
import time
import json
import logging
from typing import Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from app.core.security import decode_access_token
from app.db.session import async_session_factory
from app.db.models import AuditLog, AccessEvent
from app.streaming.event_bus import publish_event

logger = logging.getLogger("sentinel.audit")


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that intercepts requests to sensitive resources, commits an immutable

    audit log to the database, and streams the access event to the real-time detector.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()
        
        # Process request through pipeline
        response = await call_next(request)
        
        duration_ms = round((time.time() - start_time) * 1000, 2)
        path = request.url.path

        # We audit all requests to /api/v1/resources
        if path.startswith("/api/v1/resources"):
            await self._audit_and_stream(request, response, duration_ms)

        return response

    async def _audit_and_stream(self, request: Request, response: Response, duration_ms: float):
        try:
            # Extract user identity from Authorization Bearer token
            actor_username = "anonymous"
            actor_role = "unauthenticated"
            actor_id = None

            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                payload = decode_access_token(token)
                if payload:
                    actor_username = payload.get("sub", "anonymous")
                    actor_role = payload.get("role", "analyst")

            # Extract resource key from path, e.g., /api/v1/resources/{resource_key}
            path_parts = [p for p in request.url.path.strip("/").split("/") if p]
            target_resource = "RESOURCE_CATALOG"
            if len(path_parts) >= 4:
                target_resource = path_parts[3]  # e.g., PII_CUSTOMER_VAULT or ID

            # Infer classification level or default
            resource_classification = "SENSITIVE_RESOURCE"
            if "VAULT" in target_resource.upper() or "ROOT" in target_resource.upper():
                resource_classification = "RESTRICTED"
            elif "CONFIDENTIAL" in target_resource.upper() or "CRM" in target_resource.upper():
                resource_classification = "CONFIDENTIAL"

            client_ip = request.client.host if request.client else "127.0.0.1"
            forwarded_for = request.headers.get("X-Forwarded-For")
            if forwarded_for:
                client_ip = forwarded_for.split(",")[0].strip()

            action = "READ"
            if request.method == "POST":
                action = "CREATE"
            elif request.method == "PUT" or request.method == "PATCH":
                action = "UPDATE"
            elif request.method == "DELETE":
                action = "DELETE"
            elif "export" in request.url.path.lower():
                action = "EXPORT"

            # 1. Asynchronously log to database audit table
            async with async_session_factory() as session:
                audit_entry = AuditLog(
                    actor_id=actor_id,
                    actor_username=actor_username,
                    actor_role=actor_role,
                    action=action,
                    target_resource=target_resource,
                    resource_classification=resource_classification,
                    client_ip=client_ip,
                    route_path=request.url.path,
                    http_method=request.method,
                    response_status=response.status_code,
                    metadata_json=json.dumps({
                        "query_params": dict(request.query_params),
                        "latency_ms": duration_ms,
                        "user_agent": request.headers.get("User-Agent", "unknown"),
                    }),
                )
                session.add(audit_entry)
                await session.commit()

            # 2. Asynchronously publish event to streaming queue for real-time anomaly detection
            event_payload = {
                "username": actor_username,
                "user_role": actor_role,
                "resource_key": target_resource,
                "resource_type": "DATABASE" if "DB" in target_resource else "VAULT",
                "sensitivity_level": resource_classification,
                "action": action,
                "client_ip": client_ip,
                "status_code": response.status_code,
                "latency_ms": duration_ms,
                "is_synthetic": False,
                "timestamp": time.time(),
            }
            await publish_event(event_payload)

        except Exception as e:
            logger.error(f"Error in audit logging middleware: {e}", exc_info=True)
