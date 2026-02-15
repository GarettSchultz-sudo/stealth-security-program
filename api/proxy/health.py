"""
Health Check Endpoint
GET /health
"""
from fastapi import FastAPI
from datetime import datetime
import os

app = FastAPI()

@app.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "0.1.0",
        "environment": os.environ.get("ENVIRONMENT", "development"),
    }

@app.get("/health/ready")
async def readiness_check():
    """Readiness check - verify external dependencies"""
    checks = {
        "supabase": False,
        "redis": False,
    }
    
    # Check Supabase
    try:
        from _lib.db import get_supabase
        supabase = get_supabase()
        result = supabase.table("users").select("id").limit(1).execute()
        checks["supabase"] = True
    except Exception as e:
        pass
    
    # Check Redis
    try:
        from _lib.redis import get_redis
        redis = get_redis()
        await redis.ping()
        checks["redis"] = True
    except Exception as e:
        pass
    
    all_healthy = all(checks.values())
    
    return {
        "status": "ready" if all_healthy else "degraded",
        "checks": checks,
    }
