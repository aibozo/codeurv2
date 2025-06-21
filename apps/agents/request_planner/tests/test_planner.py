import pytest, json, asyncio
from apps.agents.request_planner import prompt

@pytest.mark.asyncio
async def test_build_prompt():
    # Create mock change request
    class MockCR:
        description = "Add a greeting function"
    
    cr = MockCR()
    snippets = ["def hello():", "    print('hello')"]
    
    result = prompt.build_prompt(cr, snippets)
    
    assert "CHANGE REQUEST" in result
    assert "Add a greeting function" in result
    assert "CONTEXT" in result
    assert "def hello():" in result
    assert "Return plan JSON." in result