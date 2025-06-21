import aiohttp, asyncio, json, os
from dotenv import load_dotenv
from .base import BaseProvider, LLMResponse
from .cache import cached

# Load environment variables from .env file
load_dotenv()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434/api/chat")

class OllamaProvider(BaseProvider):
    name = "ollama"

    @cached
    async def chat(self, messages, model, temperature=0.1, json_mode=False, **kw):
        pay = {
            "model": model,
            "messages": messages,
            "options": {"temperature": temperature},
            "stream": False,
        }
        if json_mode:
            pay["format"] = "json"
            
        async with aiohttp.ClientSession() as sess:
            r = await sess.post(OLLAMA_URL, json=pay, timeout=aiohttp.ClientTimeout(total=120))
            data = await r.json()
        # Ollama's simple schema -> wrap
        return LLMResponse(content=data["message"]["content"])