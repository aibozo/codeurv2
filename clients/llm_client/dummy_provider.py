"""Dummy provider for testing and CI environments"""
from .base import BaseProvider, LLMResponse

class DummyProvider(BaseProvider):
    name = "dummy"
    
    async def chat(self, messages, model, temperature=0.1, json_mode=False, **kw):
        # For testing, return predictable responses
        if json_mode:
            return LLMResponse(
                content='{"status": "ok", "provider": "dummy"}',
                tokens_prompt=10,
                tokens_completion=20,
                cost_usd=0.0
            )
        else:
            return LLMResponse(
                content="This is a dummy response from the test provider",
                tokens_prompt=5,
                tokens_completion=10,
                cost_usd=0.0
            )