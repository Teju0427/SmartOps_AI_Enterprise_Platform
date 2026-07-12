"""
FastAPI application entrypoint.

Kept intentionally minimal at this phase - routers for each business
module (equipment, pricing, maintenance, forecasting, etc.) are wired
in during Phase 7-8. Right now this exists to prove the container
boots, connects to the database, and exposes a health check that
Docker / Azure App Service / load balancers can poll.
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine
from app.api.v1.router import api_router

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    redoc_url=f"{settings.API_V1_PREFIX}/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["system"])
def health_check() -> dict:
    """Liveness + DB connectivity check used by Docker HEALTHCHECK,
    Azure App Service health probes, and load balancers."""
    db_status = "ok"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        logger.error("Database health check failed: %s", exc)
        db_status = "unreachable"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "environment": settings.ENVIRONMENT,
        "database": db_status,
    }


@app.get("/", tags=["system"])
def root() -> dict:
    return {
        "message": settings.PROJECT_NAME,
        "docs": f"{settings.API_V1_PREFIX}/docs",
    }
