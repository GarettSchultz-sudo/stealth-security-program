"""
Budget Checking and Enforcement
"""
from decimal import Decimal
from datetime import datetime, timedelta
from _lib.db import get_supabase
from _lib.redis import get_cached_budget, set_cached_budget, increment_spend_cache

async def check_budget(
    user_id: str, 
    estimated_cost: Decimal = Decimal("0"),
    model: str = None,
    agent_id: str = None
) -> dict:
    """
    Check all applicable budgets for a user
    Returns: {
        "allowed": bool,
        "action": "allow" | "alert" | "block" | "downgrade",
        "budget_name": str | None,
        "downgrade_model": str | None,
        "remaining": Decimal
    }
    """
    # Try cache first
    cached = await get_cached_budget(user_id)
    if cached and cached.get("expires_at", 0) > datetime.utcnow().timestamp():
        return cached
    
    supabase = get_supabase()
    
    # Get all active budgets for user
    result = supabase.table("budgets")\
        .select("*")\
        .eq("user_id", user_id)\
        .eq("is_active", True)\
        .execute()
    
    if not result.data:
        return {"allowed": True, "action": "allow"}
    
    for budget in result.data:
        # Check if budget applies
        if budget["scope"] == "agent" and agent_id and budget["scope_identifier"] != agent_id:
            continue
        if budget["scope"] == "model" and model and budget["scope_identifier"] != model:
            continue
        
        # Check if budget period needs reset
        if budget["reset_at"] and datetime.fromisoformat(budget["reset_at"]) < datetime.utcnow():
            await reset_budget(budget["id"])
            budget["current_spend_usd"] = 0
        
        # Check limit
        limit = Decimal(str(budget["limit_usd"]))
        current = Decimal(str(budget["current_spend_usd"]))
        remaining = limit - current
        
        if current + estimated_cost > limit:
            action = budget.get("action_on_breach", "alert")
            response = {
                "allowed": action != "block",
                "action": action,
                "budget_name": budget["name"],
                "remaining": remaining,
            }
            
            # Handle downgrade
            if action == "downgrade" and model:
                response["downgrade_model"] = get_cheaper_model(model)
            
            return response
    
    return {"allowed": True, "action": "allow"}

async def update_spend(user_id: str, cost: Decimal, budget_id: str = None):
    """Update budget spend after request completes"""
    supabase = get_supabase()
    
    # Update in database
    if budget_id:
        supabase.table("budgets")\
            .update({"current_spend_usd": supabase.rpc("increment_spend", {
                "budget_id": budget_id,
                "amount": float(cost)
            })})\
            .eq("id", budget_id)\
            .execute()
    
    # Update cache
    await increment_spend_cache(user_id, float(cost), budget_id)

async def reset_budget(budget_id: str):
    """Reset a budget for new period"""
    supabase = get_supabase()
    
    # Calculate next reset time
    result = supabase.table("budgets").select("period").eq("id", budget_id).single().execute()
    period = result.data["period"]
    
    if period == "daily":
        next_reset = datetime.utcnow() + timedelta(days=1)
    elif period == "weekly":
        next_reset = datetime.utcnow() + timedelta(weeks=1)
    else:  # monthly
        next_reset = datetime.utcnow() + timedelta(days=30)
    
    supabase.table("budgets")\
        .update({
            "current_spend_usd": 0,
            "reset_at": next_reset.isoformat()
        })\
        .eq("id", budget_id)\
        .execute()

def get_cheaper_model(current_model: str) -> str:
    """Get a cheaper alternative model"""
    downgrades = {
        "claude-opus-4": "claude-sonnet-4-20250514",
        "claude-sonnet-4-20250514": "claude-haiku-4",
        "gpt-4o": "gpt-4o-mini",
        "o1": "o3-mini",
        "gemini-2.5-pro": "gemini-2.5-flash",
    }
    return downgrades.get(current_model, current_model)
