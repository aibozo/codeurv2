import os, importlib
from dotenv import load_dotenv
from .base import BaseProvider

# Load environment variables from .env file
load_dotenv()

_PROVIDER_MAP = {
    "openai": "OpenAIProvider",
    "ollama": "OllamaProvider",
    "dummy": "DummyProvider",
}

_client: BaseProvider | None = None

def get_client() -> BaseProvider:
    global _client
    provider = os.getenv("LLM_BACKEND", "openai")  # openai | ollama | anthropic …
    
    # Check if we need to recreate the client due to provider change
    if _client is not None and hasattr(_client, 'name') and _client.name != provider:
        _client = None
    
    if _client is None:
        _MODULE = f"clients.llm_client.{provider}_provider"
        provider_class_name = _PROVIDER_MAP.get(provider, f"{provider.capitalize()}Provider")
        module = importlib.import_module(_MODULE)
        Provider: type[BaseProvider] = getattr(module, provider_class_name)
        _client = Provider()
    return _client