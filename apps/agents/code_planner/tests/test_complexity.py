import pytest
from apps.agents.code_planner.agent import complexity_of

@pytest.mark.asyncio
async def test_complexity_trivial():
    snippet = "def hello(): return 'world'"
    result = await complexity_of(snippet)
    assert result == "trivial"

@pytest.mark.asyncio
async def test_complexity_moderate():
    snippet = """def process(data):
    if data:
        for item in data:
            if item > 0:
                print(item)
    return data"""
    result = await complexity_of(snippet)
    assert result in ["trivial", "moderate"]

@pytest.mark.asyncio  
async def test_complexity_error():
    snippet = "not valid python code {"
    result = await complexity_of(snippet)
    assert result == "moderate"  # defaults to moderate on error