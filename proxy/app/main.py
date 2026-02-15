"""Main FastAPI application factory."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import get_settings
from app.models.database import init_db
from app.security import SecurityConfig, SecurityEngine, SecurityMiddleware

logger = logging.getLogger(__name__)

# Global security engine instance
_security_engine: SecurityEngine | None = None


def get_security_engine() -> SecurityEngine | None:
    """Get the global security engine instance."""
    return _security_engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup/shutdown events."""
    global _security_engine

    # Startup
    settings = get_settings()
    await init_db()

    # Initialize security engine
    if settings.security_enabled:
        security_config = SecurityConfig(
            default_detection_level=settings.security_detection_level,
            auto_kill_enabled=settings.security_auto_kill,
            auto_kill_threshold=settings.security_auto_kill_threshold,
        )
        _security_engine = SecurityEngine(config=security_config)

        # Register default action handlers
        _register_security_handlers(_security_engine)

        logger.info(f"Security engine initialized (level={settings.security_detection_level})")

    yield

    # Shutdown
    if _security_engine:
        await _security_engine.shutdown()
        logger.info("Security engine shutdown complete")


def _register_security_handlers(engine: SecurityEngine) -> None:
    """Register security action handlers."""
    from app.security import ResponseAction

    async def handle_block(**kwargs):
        """Handle block actions."""
        logger.warning(f"Request blocked: {kwargs.get('summary')}")
        return {"blocked": True}

    async def handle_alert(**kwargs):
        """Handle alert actions - send notifications."""
        summary = kwargs.get("summary")
        context = kwargs.get("context", {})

        # In production, this would send to Slack, PagerDuty, etc.
        logger.warning(
            f"Security alert: {summary.max_severity.value} - "
            f"agent={context.get('agent_id')} "
            f"threats={[t.value for t in summary.threat_types]}"
        )
        return {"alerted": True}

    async def handle_kill(**kwargs):
        """Handle kill actions - terminate agent connections."""
        context = kwargs.get("context", {})
        agent_id = context.get("agent_id")

        logger.critical(f"Kill switch activated for agent: {agent_id}")
        # In production, this would:
        # 1. Disconnect all websocket connections for this agent
        # 2. Revoke the agent's API key
        # 3. Send emergency notification
        return {"killed": True, "agent_id": agent_id}

    engine.register_action_handler(ResponseAction.BLOCK, handle_block)
    engine.register_action_handler(ResponseAction.ALERT, handle_alert)
    engine.register_action_handler(ResponseAction.KILL, handle_kill)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="ClawShell",
        description="ClawShell - AI Cost Control & Security for OpenClaw",
        version="0.1.0",
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Security middleware (add after CORS, before routes)
    if settings.security_enabled:
        app.add_middleware(
            SecurityMiddleware,
            security_engine=None,  # Will be set during lifespan
            paths_to_protect=[
                "/v1/chat/completions",
                "/v1/completions",
                "/v1/messages",
                "/v1/embeddings",
                "/api/agent/",
            ],
            excluded_paths=[
                "/health",
                "/metrics",
                "/docs",
                "/redoc",
                "/openapi.json",
            ],
        )
        # Store reference to be updated after engine init
        app.state.security_enabled = True

    # Include API routes
    app.include_router(api_router)

    # Health check endpoint
    @app.get("/health")
    async def health_check() -> dict:
        """Health check endpoint for load balancers and monitoring."""
        import shutil

        # Check which scanner tools are available
        scanners = {
            "nuclei": shutil.which("nuclei") is not None,
            "trivy": shutil.which("trivy") is not None,
            "prowler": shutil.which("prowler") is not None,
        }

        return {
            "status": "healthy",
            "scanners": scanners,
            "scanners_available": any(scanners.values()),
        }

    # Security status endpoint
    @app.get("/security/status")
    async def security_status() -> dict:
        """Get security engine status."""
        engine = get_security_engine()
        if not engine:
            return {"enabled": False}

        return {
            "enabled": True,
            "detection_level": settings.security_detection_level,
            "detectors": engine.get_detector_status(),
        }

    return app


app = create_app()
