"""
Token Counting Utilities
"""
import tiktoken

# Model to encoding mapping
ENCODING_MAP = {
    "claude": "cl100k_base",  # Claude uses similar to GPT-4
    "gpt-4": "cl100k_base",
    "gpt-3.5": "cl100k_base",
    "o1": "o200k_base",
    "o3": "o200k_base",
}

def count_tokens_anthropic(model: str, messages: list, system: str = "") -> int:
    """Estimate token count for Anthropic API"""
    encoding_name = "cl100k_base"
    
    try:
        encoding = tiktoken.get_encoding(encoding_name)
    except:
        return len(str(messages)) // 4  # Rough estimate
    
    total = 0
    
    # System prompt
    if system:
        total += len(encoding.encode(system))
    
    # Messages
    for msg in messages:
        # Add role token overhead
        total += 4  # Approximate overhead per message
        if isinstance(msg.get("content"), str):
            total += len(encoding.encode(msg["content"]))
        elif isinstance(msg.get("content"), list):
            # Handle multimodal content
            for block in msg["content"]:
                if block.get("type") == "text":
                    total += len(encoding.encode(block.get("text", "")))
                elif block.get("type") == "image":
                    # Image tokens depend on size, use estimate
                    total += 85  # Low-res image
    
    return total

def count_tokens_openai(model: str, messages: list) -> int:
    """Estimate token count for OpenAI API"""
    if "o1" in model or "o3" in model:
        encoding_name = "o200k_base"
    else:
        encoding_name = "cl100k_base"
    
    try:
        encoding = tiktoken.get_encoding(encoding_name)
    except:
        return len(str(messages)) // 4
    
    total = 0
    for msg in messages:
        total += 4  # Message overhead
        total += len(encoding.encode(msg.get("role", "")))
        total += len(encoding.encode(msg.get("content", "")))
    
    return total
