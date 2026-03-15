"""Fin Data Admin — FastAPI application entry point."""

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import structlog
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from app.config import get_settings
from app.db.session import init_db
from app.dependencies.auth import require_api_key
from app.middleware.logging import StructuredLoggingMiddleware
from app.realtime.poller import db_poller
from app.realtime.manager import realtime_manager
from app.routers import admin, analytics, auth, docker_logs, economic, markets, signals
from app.realtime import ws, sse

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize database pool and start realtime poller on startup."""
    settings = get_settings()
    await init_db(settings.database_url)
    db_poller.start()
    logger.info("app.started", environment=settings.environment)
    yield
    await db_poller.stop()
    logger.info("app.shutdown")


def create_app() -> FastAPI:
    """Application factory."""
    settings = get_settings()

    app = FastAPI(
        title="Fin Data Admin API",
        version="0.2.0",
        description="Financial data hub for stocks & crypto",
        lifespan=lifespan,
    )

    # Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(StructuredLoggingMiddleware)

    # REST Routers
    app.include_router(markets.router, prefix="/api/markets", tags=["markets"])
    app.include_router(signals.router, prefix="/api/signals", tags=["signals"])
    app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
    app.include_router(economic.router, prefix="/api/economic", tags=["economic"])
    app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
    app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
    app.include_router(docker_logs.router, prefix="/api/admin", tags=["logs"])

    # Realtime Routers
    app.include_router(ws.router, tags=["realtime"])
    app.include_router(sse.router, tags=["realtime"])

    # ── Health Check ────────────────────────────────────────────────────

    @app.get("/healthz")
    async def healthz() -> JSONResponse:
        """Health check — no auth required.

        Checks database connectivity and returns component status.
        """
        components: dict[str, str] = {"app": "ok"}

        # Check database
        try:
            from app.db.session import _engine
            if _engine is not None:
                async with _engine.connect() as conn:
                    from sqlalchemy import text
                    await conn.execute(text("SELECT 1"))
                components["db"] = "ok"
            else:
                components["db"] = "not_initialized"
        except Exception as e:
            components["db"] = "error"
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    **components,
                    "error": f"database: {str(e)}",
                },
            )

        # Check Redis
        try:
            import redis
            r = redis.from_url(settings.redis_url, decode_responses=True)
            r.ping()
            components["redis"] = "ok"
        except Exception:
            components["redis"] = "unavailable"

        # Check Celery broker
        try:
            from app.celery_client import get_celery_app
            celery = get_celery_app()
            # Just verify the app is configured
            components["celery"] = "configured"
        except Exception:
            components["celery"] = "unavailable"

        status = "ok" if components.get("db") == "ok" else "degraded"
        return JSONResponse(
            status_code=200,
            content={"status": status, **components},
        )

    # ── Diagnostics ─────────────────────────────────────────────────────

    @app.get(
        "/api/diagnostics",
        dependencies=[Depends(require_api_key)],
    )
    async def diagnostics() -> JSONResponse:
        """System diagnostics — requires API key.

        Returns database stats, realtime connection info, and poller metrics.
        """
        diag: dict = {}

        # Database pool stats
        try:
            from app.db.session import _engine
            if _engine is not None and hasattr(_engine, 'pool'):
                pool = _engine.pool
                diag["db_pool"] = {
                    "size": int(pool.size()) if hasattr(pool, 'size') else 0,
                    "checked_in": int(pool.checkedin()) if hasattr(pool, 'checkedin') else 0,
                    "checked_out": int(pool.checkedout()) if hasattr(pool, 'checkedout') else 0,
                    "overflow": int(pool.overflow()) if hasattr(pool, 'overflow') else 0,
                }
            else:
                diag["db_pool"] = "not_initialized"
        except Exception:
            diag["db_pool"] = "unavailable"

        # Realtime status
        diag["realtime"] = realtime_manager.status()

        # Poller stats
        diag["poller"] = db_poller.stats()

        return JSONResponse(content=diag)

    # ── Realtime Status ─────────────────────────────────────────────────

    @app.get(
        "/v1/realtime/status",
        dependencies=[Depends(require_api_key)],
    )
    async def realtime_status() -> JSONResponse:
        """Realtime connection status and poller diagnostics."""
        status = realtime_manager.status()
        status["poller"] = db_poller.stats()
        return JSONResponse(content=status)

    return app


app = create_app()
