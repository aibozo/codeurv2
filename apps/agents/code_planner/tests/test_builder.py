import asyncio
import pytest
from apps.core_contracts_pb2 import Plan, Step
from apps.agents.code_planner.agent import build_tasks

# Mock RAG client function
async def mock_hybrid_search(*_, **__):
    return [{"id": "blob1", "snippet": "def x(): pass"}]

# Patch the rag client
@pytest.fixture
def mock_rag(monkeypatch):
    import clients.rag_client as rag_mod
    monkeypatch.setattr(rag_mod, "hybrid_search", mock_hybrid_search)

@pytest.mark.asyncio
async def test_build_tasks(mock_rag):
    # Create a test plan
    plan = Plan(id="p1")
    plan.steps.append(
        Step(order=1, goal="add greet()", kind="ADD", path="src/app.py")
    )
    
    # Build tasks from the plan
    tb = await build_tasks(plan)
    
    # Assertions
    assert tb.plan_id == "p1"
    assert len(tb.tasks) == 1
    
    task = tb.tasks[0]
    assert task.parent_plan_id == "p1"
    assert task.step_number == 1
    assert task.goal == "add greet()"
    assert task.kind == "ADD"
    assert task.path == "src/app.py"
    assert task.complexity in ("trivial", "moderate", "complex")
    assert len(task.blob_ids) == 1
    assert task.blob_ids[0] == "blob1"