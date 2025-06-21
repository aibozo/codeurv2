import pytest
import os
from clients.llm_client import chat, json_chat, LLMResponse

@pytest.mark.asyncio
async def test_chat_with_dummy_provider():
    # Set dummy provider for testing
    os.environ['LLM_BACKEND'] = 'dummy'
    
    # Clear any cached client
    import clients.llm_client.router as router
    router._client = None
    
    result = await chat(
        messages=[{"role": "user", "content": "Hello"}],
        model="gpt-4o-mini"
    )
    
    assert isinstance(result, LLMResponse)
    assert result.content == "This is a dummy response from the test provider"
    assert result.tokens_prompt == 5
    assert result.tokens_completion == 10
    assert result.cost_usd == 0.0

@pytest.mark.asyncio
async def test_json_chat_with_dummy_provider():
    # Set dummy provider for testing
    os.environ['LLM_BACKEND'] = 'dummy'
    
    # Clear any cached client
    import clients.llm_client.router as router
    router._client = None
    
    result = await json_chat(
        messages=[{"role": "user", "content": "Generate JSON"}],
        model="gpt-4o-mini"
    )
    
    assert result == '{"status": "ok", "provider": "dummy"}'

def test_cache_key_generation():
    from clients.llm_client.cache import _key
    
    # Test that same inputs produce same key
    key1 = _key("gpt-4", [{"role": "user", "content": "test"}], temperature=0.5)
    key2 = _key("gpt-4", [{"role": "user", "content": "test"}], temperature=0.5)
    assert key1 == key2
    
    # Test that different inputs produce different keys
    key3 = _key("gpt-4", [{"role": "user", "content": "different"}], temperature=0.5)
    assert key1 != key3

def test_router_provider_selection():
    import clients.llm_client.router as router
    
    # Test provider selection
    os.environ['LLM_BACKEND'] = 'dummy'
    router._client = None  # Clear cache
    
    client = router.get_client()
    assert client.name == "dummy"