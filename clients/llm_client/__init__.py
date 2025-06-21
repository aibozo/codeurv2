from .router import get_client
import json

async def chat(messages: list[dict], model: str, **kw):
    return await get_client().chat(messages=messages, model=model, **kw)

# Backwards-compat helpers so existing agent code is 1-line diff
async def json_chat(messages, model):
    res = await chat(messages, model, json_mode=True)
    return res.content   # keep same shape as previous parse_json()

# Export commonly used types
from .base import LLMResponse, BaseProvider

__all__ = ["chat", "json_chat", "LLMResponse", "BaseProvider", "get_client"]