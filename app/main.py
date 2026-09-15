"""Main FastAPI application entrypoint for SentinelShield."""
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from slowapi.errors import RateLimitExceeded

from slowapi.middleware import SlowAPIMiddleware
from app.config import settings
from app.core.rate_limiter import limiter, rate_limit_exceeded_handler
from app.core.audit_middleware import AuditLoggingMiddleware
from app.db.init_db import init_db
from app.streaming.event_worker import start_event_worker, stop_event_worker
from app.simulator.traffic_generator import simulator
from app.streaming.event_bus import get_queue_size
from app.streaming.connection_manager import ws_manager

# API Routers
from app.api.v1.auth import router as auth_router
from app.api.v1.resources import router as resources_router
from app.api.v1.audit import router as audit_router
from app.api.v1.anomalies import router as anomalies_router
from app.api.v1.graph import router as graph_router
from app.api.v1.simulator import router as simulator_router
from app.api.v1.websocket import router as ws_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("sentinel.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management: startup & teardown hooks."""
    logger.info("Starting SentinelShield platform...")
    # 1. Initialize and seed database
    await init_db()

    # 2. Start streaming worker
    start_event_worker()

    # 3. Start synthetic traffic simulator
    if settings.SIMULATOR_ENABLED_AT_START:
        simulator.start(settings.SIMULATOR_DEFAULT_DELAY_SECONDS)

    logger.info("SentinelShield startup complete. Real-time anomaly detection active.")
    yield

    # Teardown
    logger.info("Shutting down SentinelShield platform...")
    simulator.stop()
    stop_event_worker()
    logger.info("Shutdown complete.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Real-Time Data Access Anomaly Detection System with Security Hardening",
    lifespan=lifespan,
)

# SlowAPI Rate Limiter State & Exception Handling
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Audit Logging & Streaming Middleware
app.add_middleware(AuditLoggingMiddleware)

# Include API Routers
api_v1_prefix = "/api/v1"
app.include_router(auth_router, prefix=api_v1_prefix)
app.include_router(resources_router, prefix=api_v1_prefix)
app.include_router(audit_router, prefix=api_v1_prefix)
app.include_router(anomalies_router, prefix=api_v1_prefix)
app.include_router(graph_router, prefix=api_v1_prefix)
app.include_router(simulator_router, prefix=api_v1_prefix)
app.include_router(ws_router)  # Includes /ws/dashboard

# Static assets and template engine
base_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(base_dir, "static")
templates_dir = os.path.join(base_dir, "templates")

os.makedirs(static_dir, exist_ok=True)
os.makedirs(templates_dir, exist_ok=True)

app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_dashboard(request: Request):
    """Serve the primary Live Security Operations Center (SOC) dashboard."""
    return templates.TemplateResponse(request=request, name="index.html", context={"project_name": settings.PROJECT_NAME})


@app.get("/health", tags=["System Health"])
async def health_check():
    """System health check and real-time operational telemetry."""
    return {
        "status": "HEALTHY",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "active_ws_connections": ws_manager.count(),
        "event_queue_depth": get_queue_size(),
        "simulator": simulator.get_status(),
    }
