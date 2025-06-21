import functools, hashlib, json, pathlib, os
from dotenv import load_dotenv
from .base import LLMResponse

# Load environment variables from .env file
load_dotenv()

_CACHE_DIR = pathlib.Path(os.getenv("LLM_CACHE_DIR", ".llm_cache"))
_CACHE_DIR.mkdir(exist_ok=True)

def _key(model, messages, **kw):
    data = {"m": model, "msg": messages, "kw": kw}
    h = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
    return _CACHE_DIR / f"{h}.json"

def cached(func):
    async def wrapper(self, messages, model, **kw):
        # Create cache key
        k = _key(model, messages, **kw)
        if k.exists():
            return LLMResponse(**json.loads(k.read_text()))
        res: LLMResponse = await func(self, messages, model, **kw)
        k.write_text(json.dumps(res.__dict__))
        return res
    return wrapper