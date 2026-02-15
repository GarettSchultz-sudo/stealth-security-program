"""
API Key Authentication
"""
import hashlib
import os
from _lib.db import get_supabase

async def validate_api_key(api_key: str) -> tuple[str, str]:
    """
    Validate API key and return (user_id, plan)
    Raises HTTPException if invalid
    """
    if not api_key:
        from fastapi import HTTPException
        raise HTTPException(401, "Missing API key")
    
    # Hash the key for lookup
    key_hash = hashlib.sha256(
        (api_key + os.environ.get("API_KEY_SALT", "")).encode()
    ).hexdigest()
    
    supabase = get_supabase()
    result = supabase.table("api_keys")\
        .select("user_id, is_active, users!inner(plan)")\
        .eq("key_hash", key_hash)\
        .eq("is_active", True)\
        .execute()
    
    if not result.data:
        from fastapi import HTTPException
        raise HTTPException(401, "Invalid API key")
    
    key_data = result.data[0]
    return (key_data["user_id"], key_data["users"]["plan"])

def hash_api_key(api_key: str) -> str:
    """Hash an API key for storage"""
    salt = os.environ.get("API_KEY_SALT", "default-salt")
    return hashlib.sha256((api_key + salt).encode()).hexdigest()

def generate_api_key() -> str:
    """Generate a new API key"""
    import secrets
    return f"acc_{secrets.token_hex(16)}"
