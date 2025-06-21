from __future__ import annotations
import abc, typing as _t
from dataclasses import dataclass

@dataclass
class LLMResponse:
    content: str
    tokens_prompt: int = 0
    tokens_completion: int = 0
    cost_usd: float = 0.0

class BaseProvider(abc.ABC):
    """All concrete providers must implement `chat`."""

    name: str

    @abc.abstractmethod
    async def chat(
        self,
        messages: list[dict],
        model: str,
        temperature: float = 0.1,
        json_mode: bool = False,
        **kwargs,
    ) -> LLMResponse: ...