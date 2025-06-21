import os, asyncio, backoff, logging
from dotenv import load_dotenv
from .base import BaseProvider, LLMResponse
from .cache import cached
import openai

# Load environment variables from .env file
load_dotenv()

log = logging.getLogger("llm.openai")

_API_KEY = os.getenv("OPENAI_API_KEY")
if _API_KEY:
    openai.api_key = _API_KEY

_OPENAI_COST = {  # very simplified cost table USD / 1K tokens
    "gpt-4o-mini": (0.005, 0.015),   # (prompt, completion)
    "gpt-4o":      (0.01, 0.03),
}

class OpenAIProvider(BaseProvider):
    name = "openai"

    @cached
    @backoff.on_exception(backoff.expo, openai.APIError, max_time=60)
    async def chat(self, messages, model, temperature=0.1, json_mode=False, **kw):
        if not _API_KEY:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        log.debug("OpenAI call %s", model)
        resp = await openai.ChatCompletion.acreate(
            model=model,
            messages=messages,
            temperature=temperature,
            response_format=( {"type":"json_object"} if json_mode else "text" ),
            **kw,
        )
        choice = resp.choices[0].message
        usage = resp.usage                    # prompt_tokens, completion_tokens
        p_cost, c_cost = _OPENAI_COST.get(model, (0, 0))
        usd = (usage.prompt_tokens / 1000) * p_cost + (usage.completion_tokens / 1000) * c_cost
        return LLMResponse(
            content=choice.content,
            tokens_prompt=usage.prompt_tokens,
            tokens_completion=usage.completion_tokens,
            cost_usd=usd,
        )