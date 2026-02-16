"""Main API router combining all v1 routes."""

from fastapi import APIRouter

from app.api.v1 import agents, analytics, auth, budgets, proxy, routing, scan

api_router = APIRouter()

# Include all v1 routes
api_router.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
api_router.include_router(proxy.router, prefix="/v1", tags=["proxy"])
api_router.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])
api_router.include_router(budgets.router, prefix="/api/v1/budgets", tags=["budgets"])
api_router.include_router(agents.router, prefix="/api/v1/agents", tags=["agents"])
api_router.include_router(routing.router, prefix="/api/v1/routing", tags=["routing"])
api_router.include_router(scan.router, prefix="/api/v1", tags=["scanning"])
