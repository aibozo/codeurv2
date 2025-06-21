import os
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

import asyncio
import json
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock

from apps.core_contracts_pb2 import CodingTask, CommitResult, TaskBundle


class TestCodingAgent:
    @pytest.mark.asyncio
    async def test_llm_patch_mock(self):
        """Test LLM patch generation with mock mode"""
        from apps.agents.coding_agent.agent import llm_patch, MOCK_LLM
        
        # Direct test without mocking env vars since it's already set
        task = CodingTask(
            id="test-task-1",
            goal="Add greeting function",
            path="src/hello.py",
            kind="ADD"
        )
        
        result = await llm_patch(task, "context")
        
        assert "diff" in result
        assert "reasoning" in result
        if MOCK_LLM:
            assert result["reasoning"] == "Mock patch for testing"
    
    def test_apply_patch_valid(self):
        """Test applying a valid patch"""
        from apps.agents.coding_agent.agent import apply_patch
        
        # Mock repo
        mock_repo = Mock()
        mock_repo.working_dir = "/tmp/test"
        
        valid_diff = """--- a/test.txt
+++ b/test.txt
@@ -1 +1,2 @@
 Hello
+World"""
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            result = apply_patch(mock_repo, valid_diff)
            
            assert result is True
            mock_run.assert_called_once()
    
    def test_apply_patch_invalid(self):
        """Test applying an invalid patch"""
        from apps.agents.coding_agent.agent import apply_patch
        
        mock_repo = Mock()
        mock_repo.working_dir = "/tmp/test"
        
        invalid_diff = "not a valid diff"
        
        result = apply_patch(mock_repo, invalid_diff)
        assert result is False
    
    def test_run_selfcheck(self):
        """Test self-check pipeline"""
        from apps.agents.coding_agent.agent import run_selfcheck
        from pathlib import Path
        
        with patch("pathlib.Path.glob") as mock_glob:
            mock_glob.return_value = [Path("test.py")]
            
            with patch("shutil.which") as mock_which:
                mock_which.return_value = "/usr/bin/black"
                
                with patch("subprocess.run") as mock_run:
                    # All checks pass
                    mock_run.return_value.returncode = 0
                    ok, notes = run_selfcheck("/tmp/test")
                    
                    assert ok is True
                    assert len(notes) == 0
    
    @pytest.mark.asyncio
    async def test_process_task_success(self):
        """Test successful task processing"""
        from apps.agents.coding_agent.agent import process_task
        
        task = CodingTask(
            id="test-task-1",
            parent_plan_id="plan-1",
            step_number=1,
            goal="Add hello function",
            path="src/hello.py",
            kind="ADD",
            blob_ids=[],
            complexity="trivial"
        )
        
        # Mock all external dependencies
        with patch("apps.agents.coding_agent.agent.Repo") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo_cls.clone_from.return_value = mock_repo
            mock_repo.working_dir = "/tmp/test"
            mock_repo.head.commit.hexsha = "abc123"
            
            with patch("apps.agents.coding_agent.agent.llm_patch") as mock_llm:
                mock_llm.return_value = {
                    "diff": "--- a/src/hello.py\n+++ b/src/hello.py\n@@ -1 +1,2 @@\nprint('hi')\n+def hello(): pass",
                    "reasoning": "Added hello function"
                }
                
                with patch("apps.agents.coding_agent.agent.apply_patch") as mock_apply:
                    mock_apply.return_value = True
                    
                    with patch("apps.agents.coding_agent.agent.run_selfcheck") as mock_check:
                        mock_check.return_value = (True, [])
                        
                        with patch("apps.agents.coding_agent.agent.producer") as mock_producer:
                            mock_send = AsyncMock()
                            mock_producer.send = mock_send
                            
                            with patch("tempfile.mkdtemp") as mock_mkdtemp:
                                mock_mkdtemp.return_value = "/tmp/test"
                                
                                with patch("shutil.rmtree"):
                                    await process_task(task)
                                    
                                    # Verify success result was sent
                                    mock_send.assert_called_once()
                                    topic, result = mock_send.call_args[0]
                                    assert topic == "commit.result.out"
                                    assert result.status == "SUCCESS"
                                    assert result.task_id == "test-task-1"
    
    @pytest.mark.asyncio
    async def test_process_task_soft_fail(self):
        """Test task processing with soft failure"""
        from apps.agents.coding_agent.agent import process_task
        
        task = CodingTask(
            id="test-task-2",
            goal="Add function",
            path="src/test.py",
            kind="ADD"
        )
        
        with patch("apps.agents.coding_agent.agent.Repo") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo_cls.clone_from.return_value = mock_repo
            mock_repo.working_dir = "/tmp/test"
            
            with patch("apps.agents.coding_agent.agent.llm_patch") as mock_llm:
                mock_llm.return_value = {"diff": "invalid", "reasoning": "test"}
                
                with patch("apps.agents.coding_agent.agent.apply_patch") as mock_apply:
                    mock_apply.return_value = False  # Patch fails
                    
                    with patch("apps.agents.coding_agent.agent.producer") as mock_producer:
                        mock_send = AsyncMock()
                        mock_producer.send = mock_send
                        
                        with patch("tempfile.mkdtemp") as mock_mkdtemp:
                            mock_mkdtemp.return_value = "/tmp/test"
                            
                            with patch("shutil.rmtree"):
                                await process_task(task)
                                
                                # Verify soft fail result
                                mock_send.assert_called_once()
                                topic, result = mock_send.call_args[0]
                                assert result.status == "SOFT_FAIL"
                                assert result.task_id == "test-task-2"