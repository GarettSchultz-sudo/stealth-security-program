"""
Smart Model Routing Logic
"""
from _lib.db import get_supabase

async def get_routing_rules(user_id: str) -> list[dict]:
    """Get routing rules for a user"""
    # TODO: Implement routing_rules table
    # For now, return empty list
    return []

def apply_routing(
    model: str, 
    messages: list, 
    rules: list[dict]
) -> tuple[str, dict]:
    """
    Apply routing rules to potentially redirect request
    Returns: (final_model, routing_metadata)
    """
    metadata = {"original_model": model, "routed": False}
    
    for rule in rules:
        if rule_matches(rule, model, messages):
            new_model = rule.get("target_model", model)
            if new_model != model:
                metadata["routed"] = True
                metadata["routing_rule"] = rule.get("name")
                metadata["reason"] = rule.get("reason")
                return new_model, metadata
    
    return model, metadata

def rule_matches(rule: dict, model: str, messages: list) -> bool:
    """Check if a routing rule matches current request"""
    # Check model pattern
    if rule.get("source_model_pattern"):
        import re
        if not re.match(rule["source_model_pattern"], model):
            return False
    
    # Check message count threshold
    if rule.get("min_messages"):
        if len(messages) < rule["min_messages"]:
            return False
    
    # Check for keywords in messages
    if rule.get("content_keywords"):
        content = " ".join([m.get("content", "") for m in messages])
        keywords = rule["content_keywords"]
        if not any(kw in content for kw in keywords):
            return False
    
    return True
