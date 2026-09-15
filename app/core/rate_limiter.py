"""Rate limiting configuration using SlowAPI."""
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from app.config import settings

# Key function that falls back to header if behind proxy or auth token
def rate_limit_key_func(request: Request) -> str:
    """Determine rate limit key by authorization token or client IP."""
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header
    return get_remote_address(request) or "127.0.0.1"


limiter = Limiter(
    key_func=rate_limit_key_func,
    default_limits=[settings.RATE_LIMIT_DEFAULT],
    storage_uri="memory://",
)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """Custom response for rate limit violations."""
    return JSONResponse(
        status_code=429,
        content={
            "error": "Rate limit exceeded",
            "detail": f"Too many requests. Limit: {exc.detail}",
            "retry_after_seconds": 60,
        },
        headers={"Retry-After": "60"},
    )
