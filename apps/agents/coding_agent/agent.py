import os
import asyncio
import subprocess
import tempfile
import uuid
import json
import logging
import shutil
from pathlib import Path

from unidiff import PatchSet
from git import Repo, GitCommandError
from prometheus_client import Counter, start_http_server

from apps.core_contracts_pb2 import CodingTask, CommitResult, TaskBundle
from clients.kafka_utils import producer, consumer
from clients import rag_client, srm_client
from apps.orchestrator import topics as T
import openai
import anyio

# Setup logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("coding-agent")

# Environment configuration
LLM_MODEL = os.getenv("CODING_MODEL", "gpt-4o-mini-code-30k")
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "2"))
REMOTE_REPO = os.getenv("REMOTE_REPO", "https://github.com/your-org/self-healing-code")
MOCK_LLM = os.getenv("MOCK_LLM", "0") == "1"

# Prometheus metrics
PATCH_GEN = Counter("ca_patches_total", "Patches generated", ["result"])
COMMIT_CNT = Counter("ca_commits_total", "Commits made", ["status"])
start_http_server(9600)

# Kafka configuration
KAFKA_CONFIG = {"topics": {"subscribe": [T.TASK]}}

async def llm_patch(task: CodingTask, ctx_text: str) -> dict:
    """Generate a patch using LLM or mock response"""
    if MOCK_LLM:
        return {
            "diff": "--- a/README.md\n+++ b/README.md\n@@ -1,1 +1,2 @@\n# Self-Healing Code\n+\n",
            "reasoning": "Mock patch for testing"
        }
    
    system = """You are Coding-Agent. Generate a unified diff patch to accomplish the task.
Return JSON with:
- diff: the unified diff patch (git format)
- reasoning: brief explanation of changes"""
    
    user = f"""TASK GOAL:
{task.goal}

FILE PATH:
{task.path or 'N/A'}

TASK KIND:
{task.kind}

CONTEXT (read-only reference):
{ctx_text[:3000]}

Generate a minimal, focused patch that accomplishes the goal."""
    
    try:
        # Use new OpenAI API
        client = openai.AsyncOpenAI()
        resp = await client.chat.completions.create(
            model=LLM_MODEL,
            temperature=0.1,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(resp.choices[0].message.content)
    except Exception as e:
        log.error(f"LLM call failed: {e}")
        return {"diff": "", "reasoning": f"Error: {str(e)}"}

def apply_patch(repo: Repo, diff: str) -> bool:
    """Apply a unified diff patch to the repository"""
    try:
        # Validate diff syntax
        PatchSet(diff)
        
        # Apply the patch
        proc = subprocess.run(
            ["git", "apply", "-"],
            input=diff.encode(),
            cwd=repo.working_dir,
            capture_output=True,
            text=True
        )
        
        if proc.returncode == 0:
            return True
        else:
            log.warning(f"Patch rejected: {proc.stderr}")
            return False
    except Exception as e:
        log.warning(f"Patch validation failed: {e}")
        return False

def run_selfcheck(repo_dir: str) -> tuple[bool, list]:
    """Run format/lint/test checks on the code"""
    notes = []
    
    def _run(cmd):
        result = subprocess.run(
            cmd,
            cwd=repo_dir,
            capture_output=True,
            text=True,
            shell=False
        )
        if result.returncode != 0:
            notes.append(f"{' '.join(cmd)}: {result.stdout}\n{result.stderr}")
        return result.returncode == 0
    
    # Skip checks if files don't exist
    py_files = list(Path(repo_dir).glob("**/*.py"))
    if not py_files:
        return True, []
    
    # Run checks (fail fast)
    checks_pass = True
    
    # Black formatting check
    if shutil.which("black"):
        checks_pass = _run(["black", "--check", "."])
    
    # Ruff linting
    if checks_pass and shutil.which("ruff"):
        checks_pass = _run(["ruff", "check", "."])
    
    # Fast tests (if available)
    if checks_pass and Path(repo_dir, "pytest.ini").exists():
        checks_pass = _run(["pytest", "-q", "-m", "fast", "--tb=short"])
    
    return checks_pass, notes

async def process_task(task: CodingTask):
    """Process a single coding task"""
    workdir = Path(tempfile.mkdtemp())
    log.info(f"Processing task {task.id} in {workdir}")
    
    try:
        # Clone repository using git cache if available
        repo_branch = task.path.split("/")[0] if task.path and "/" in task.path else "main"
        
        # Check for git cache reference
        cache_ref = os.getenv("GIT_CACHE_REF")
        if cache_ref and Path(cache_ref).exists():
            log.info(f"Using git cache reference: {cache_ref}")
            # Clone with reference to cache
            clone_cmd = [
                "git", "clone",
                "--reference-if-able", cache_ref,
                "--depth", "1",
                "--branch", repo_branch,
                REMOTE_REPO,
                str(workdir)
            ]
            subprocess.run(clone_cmd, check=True)
            repo = Repo(workdir)
        else:
            # Fallback to regular clone
            repo = Repo.clone_from(
                REMOTE_REPO,
                workdir,
                depth=1,
                branch=repo_branch
            )
        
        # Get RAG context if blob_ids provided
        ctx_text = ""
        if task.blob_ids:
            snippets = []
            async for result in rag_client.snippet_stream(task.blob_ids):
                snippets.append(result.snippet)
            ctx_text = "\n\n".join(snippets)
        
        # Try to generate and apply patch
        notes = []  # Initialize notes list
        for attempt in range(MAX_RETRIES + 1):
            patch_json = await llm_patch(task, ctx_text)
            
            if not patch_json.get("diff"):
                log.warning(f"Empty diff generated for task {task.id}")
                continue
            
            if not apply_patch(repo, patch_json["diff"]):
                PATCH_GEN.labels("invalid").inc()
                continue
            
            # Run self-checks
            ok, notes = run_selfcheck(str(workdir))
            
            if ok:
                PATCH_GEN.labels("success").inc()
                
                # Create branch and commit
                branch_name = f"agt/{task.id}"
                repo.git.checkout("-b", branch_name)
                repo.git.add(all=True)
                
                commit_msg = f"{task.kind.lower()}: {task.goal}\n\n[agent:{task.id}]"
                repo.git.commit("-m", commit_msg)
                
                # Push to remote
                try:
                    repo.git.push("origin", branch_name)
                except GitCommandError as e:
                    log.error(f"Push failed: {e}")
                    notes.append(f"Push failed: {str(e)}")
                    ok = False
                
                if ok:
                    commit_sha = repo.head.commit.hexsha
                    
                    # Claim SRM leases if any
                    if hasattr(task, 'reserved_lease_ids'):
                        for lease_id in task.reserved_lease_ids:
                            try:
                                await srm_client.claim(
                                    lease_id=int(lease_id),
                                    commit_sha=commit_sha
                                )
                            except Exception as e:
                                log.warning(f"SRM claim failed for lease {lease_id}: {e}")
                    
                    # Emit success result
                    result = CommitResult(
                        task_id=task.id,
                        commit_sha=commit_sha,
                        status="SUCCESS",
                        branch_name=branch_name,
                        notes=[]
                    )
                    
                    await producer.send(T.CRES, result)
                    COMMIT_CNT.labels("success").inc()
                    return
            else:
                PATCH_GEN.labels("fail").inc()
                
                # Add failure notes to context for retry
                if attempt < MAX_RETRIES:
                    ctx_text += "\n\n# SELF-CHECK FAILURES\n" + "\n".join(notes)
                    notes = []  # Clear for next attempt
        
        # All attempts failed - emit soft fail
        result = CommitResult(
            task_id=task.id,
            commit_sha="",
            status="SOFT_FAIL",
            branch_name="",
            notes=notes
        )
        
        await producer.send(T.CRES, result)
        COMMIT_CNT.labels("soft_fail").inc()
        
    except Exception as e:
        log.error(f"Task {task.id} hard failed: {e}", exc_info=True)
        
        # Emit hard fail
        result = CommitResult(
            task_id=task.id,
            commit_sha="",
            status="HARD_FAIL",
            branch_name="",
            notes=[str(e)]
        )
        
        await producer.send(T.CRES, result)
        COMMIT_CNT.labels("hard_fail").inc()
        
    finally:
        # Cleanup
        if workdir.exists():
            shutil.rmtree(workdir)

async def main_loop():
    """Main event loop"""
    log.info("Coding-Agent started")
    
    async with consumer.configure(KAFKA_CONFIG) as c:
        async for topic, msg in c:
            if topic == T.TASK:
                bundle = TaskBundle()
                bundle.ParseFromString(msg)
                
                log.info(f"Received TaskBundle for plan {bundle.plan_id} with {len(bundle.tasks)} tasks")
                
                # Process tasks concurrently
                await asyncio.gather(*[
                    process_task(task) for task in bundle.tasks
                ], return_exceptions=True)

if __name__ == "__main__":
    asyncio.run(main_loop())