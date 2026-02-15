"""
FastAPI Middleware for ClawShell Security

Integrates the security engine into the proxy request/response pipeline.
"""

import json
import logging
import time
import uuid
from collections.abc import Callable
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Message

from app.security.config import get_security_config
from app.security.engine import SecurityEngine
from app.security.models import ResponseAction

logger = logging.getLogger(__name__)


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware that intercepts requests/responses for security analysis.

    Flow:
    1. Pre-process: Analyze request, potentially block
    2. Pass through to route handler (if allowed)
    3. Post-process: Analyze response, potentially modify/withhold
    """

    def __init__(
        self,
        app: ASGIApp,
        security_engine: SecurityEngine | None = None,
        paths_to_protect: list[str] | None = None,
        excluded_paths: list[str] | None = None,
    ):
        super().__init__(app)
        self._engine = security_engine
        self.config = get_security_config()

        # Default paths to protect (LLM API endpoints)
        self.paths_to_protect = paths_to_protect or [
            "/v1/chat/completions",
            "/v1/completions",
            "/v1/messages",
            "/v1/embeddings",
        ]

        # Paths to skip security
        self.excluded_paths = excluded_paths or [
            "/health",
            "/metrics",
            "/favicon.ico",
        ]

    @property
    def engine(self) -> SecurityEngine:
        """Get the security engine, initializing if needed."""
        if self._engine is None:
            # Try to get from global (set during lifespan)
            from app.main import get_security_engine

            global_engine = get_security_engine()
            if global_engine:
                self._engine = global_engine
            else:
                # Fallback: create new instance
                self._engine = SecurityEngine()
        return self._engine

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request through security pipeline."""
        start_time = time.time()

        # Skip excluded paths
        if any(request.url.path.startswith(p) for p in self.excluded_paths):
            return await call_next(request)

        # Only protect specific paths
        should_protect = any(request.url.path.startswith(p) for p in self.paths_to_protect)

        if not should_protect:
            return await call_next(request)

        # Extract context
        context = self._extract_context(request)

        # Read request body
        try:
            request_body = await request.body()
            request_data = json.loads(request_body) if request_body else {}
        except json.JSONDecodeError:
            request_data = {}

        # Pre-request security analysis
        request_summary = await self.engine.analyze_request(request_data, context)

        # Handle block actions
        if ResponseAction.BLOCK in request_summary.actions_required:
            logger.warning(
                f"Request blocked: {request_summary.max_severity.value} - "
                f"{[t.value for t in request_summary.threat_types]}"
            )
            await self.engine.take_actions(
                request_summary,
                request_data=request_data,
                context=context,
            )
            return self._block_response(request_summary)

        # Handle quarantine
        if ResponseAction.QUARANTINE in request_summary.actions_required:
            await self._quarantine_request(request, request_data, request_summary, context)

        # Store request context for response analysis
        context["_request_summary"] = request_summary
        context["_request_data"] = request_data

        # Reconstruct request with body for downstream handlers
        async def receive() -> Message:
            return {"type": "http.request", "body": request_body}

        # Process request
        response = await call_next(request)

        # Post-response security analysis
        if self._should_analyze_response(response):
            response_summary = await self._analyze_response(response, context, request_summary)

            # Handle response-level blocks
            if ResponseAction.BLOCK in response_summary.actions_required:
                logger.warning("Response blocked by security policy")
                return self._block_response(response_summary)

            # Handle warnings
            if ResponseAction.WARN in response_summary.actions_required:
                response = self._add_warning_header(response, response_summary)

            # Take any remaining actions
            await self.engine.take_actions(
                response_summary,
                request_data=request_data,
                response_data=await self._get_response_body(response),
                context=context,
            )

        # Log timing
        elapsed_ms = (time.time() - start_time) * 1000
        if elapsed_ms > self.config.max_total_middleware_ms:
            logger.warning(f"Security middleware took {elapsed_ms:.1f}ms")

        return response

    def _extract_context(self, request: Request) -> dict[str, Any]:
        """Extract security context from request."""
        context = {
            "request_id": str(uuid.uuid4()),
            "path": request.url.path,
            "method": request.method,
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent", ""),
            "timestamp": time.time(),
        }

        # Extract org/user info from headers
        context["org_id"] = request.headers.get("x-org-id")
        context["user_id"] = request.headers.get("x-user-id")
        context["agent_id"] = request.headers.get("x-agent-id")
        context["skill_id"] = request.headers.get("x-skill-id")

        # Extract API key info (hashed for logging)
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            key = auth_header[7:]
            context["api_key_prefix"] = key[:8] + "..." if len(key) > 8 else "***"

        return context

    def _block_response(self, summary) -> Response:
        """Create a blocked response."""
        return Response(
            content=json.dumps(
                {
                    "error": {
                        "type": "security_violation",
                        "message": "Request blocked by security policy",
                        "severity": summary.max_severity.value,
                        "threat_types": [t.value for t in summary.threat_types],
                    }
                }
            ),
            status_code=403,
            media_type="application/json",
            headers={
                "X-Security-Block": "true",
                "X-Security-Severity": summary.max_severity.value,
            },
        )

    async def _quarantine_request(
        self,
        request: Request,
        request_data: dict[str, Any],
        summary,
        context: dict[str, Any],
    ) -> None:
        """Quarantine a request for later review."""
        # In production, this would encrypt and store in database
        logger.info(
            f"Quarantining request {context.get('request_id')} - {summary.max_severity.value}"
        )

    def _should_analyze_response(self, response: Response) -> bool:
        """Check if response should be analyzed."""
        # Only analyze successful JSON responses
        return response.status_code == 200 and response.headers.get("content-type", "").startswith(
            "application/json"
        )

    async def _analyze_response(
        self,
        response: Response,
        context: dict[str, Any],
        request_summary,
    ) -> Any:
        """Analyze response for security issues."""
        # Capture response body
        response_body = await self._get_response_body(response)
        response_data = json.loads(response_body) if response_body else {}

        return await self.engine.analyze_response(response_data, context)

    async def _get_response_body(self, response: Response) -> bytes:
        """Get response body, handling streaming responses."""
        # For non-streaming, body is available
        if hasattr(response, "body"):
            return response.body

        # For streaming, we'd need to capture chunks
        # This is a simplified version
        return b"{}"

    def _add_warning_header(self, response: Response, summary) -> Response:
        """Add security warning to response."""
        # Add warning header
        response.headers["X-Security-Warning"] = "true"
        response.headers["X-Security-Warning-Level"] = summary.max_severity.value
        return response


class StreamingSecurityInterceptor:
    """
    Intercepts streaming responses for real-time security analysis.

    This allows detecting threats mid-stream and terminating if needed.
    """

    def __init__(
        self,
        engine: SecurityEngine,
        context: dict[str, Any],
        buffer_size: int = 1000,
    ):
        self.engine = engine
        self.context = context
        self.buffer_size = buffer_size
        self._buffer: list[str] = []
        self._total_chars = 0
        self._killed = False

    async def intercept_chunk(self, chunk: str) -> str | None:
        """
        Intercept a streaming chunk.

        Returns:
            - The chunk if allowed
            - None if stream should be terminated
        """
        if self._killed:
            return None

        # Buffer the chunk
        self._buffer.append(chunk)
        self._total_chars += len(chunk)

        # Periodic analysis (every buffer_size chars)
        if self._total_chars >= self.buffer_size:
            combined = "".join(self._buffer)

            # Quick analysis (run in background)
            # In production, this would use a sliding window approach
            summary = await self._quick_analyze(combined)

            if ResponseAction.KILL in summary.actions_required:
                logger.warning("Stream killed by security policy")
                self._killed = True
                return None

            if ResponseAction.BLOCK in summary.actions_required:
                logger.warning("Stream blocked by security policy")
                self._killed = True
                return None

            # Reset buffer but keep last 100 chars for context
            self._buffer = [combined[-100:]] if len(combined) > 100 else [combined]
            self._total_chars = len(self._buffer[0])

        return chunk

    async def _quick_analyze(self, text: str) -> Any:
        """Quick analysis of buffered text."""
        # Create pseudo-response for analysis
        response_data = {
            "content": [{"type": "text", "text": text}],
        }
        return await self.engine.analyze_response(response_data, self.context)

    def is_killed(self) -> bool:
        """Check if stream was killed."""
        return self._killed


def create_security_middleware(
    app: ASGIApp,
    config: dict[str, Any] | None = None,
) -> SecurityMiddleware:
    """
    Factory function to create security middleware with configuration.

    Args:
        app: The ASGI application
        config: Optional configuration dictionary

    Returns:
        Configured SecurityMiddleware instance
    """
    engine = SecurityEngine()

    if config:
        # Apply configuration
        if "paths_to_protect" in config:
            engine.paths_to_protect = config["paths_to_protect"]
        if "excluded_paths" in config:
            engine.excluded_paths = config["excluded_paths"]

    return SecurityMiddleware(
        app=app,
        security_engine=engine,
        paths_to_protect=config.get("paths_to_protect") if config else None,
        excluded_paths=config.get("excluded_paths") if config else None,
    )
