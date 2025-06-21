import pytest, httpx, asyncio, os
import qdrant_client
from apps.rag_service.ingest import ingest_git_commit

def qdrant_available():
    """Check if Qdrant is available"""
    try:
        client = qdrant_client.QdrantClient(url=os.getenv("QDRANT_URL", "http://localhost:6333"))
        client.get_collections()
        return True
    except Exception:
        return False

@pytest.mark.asyncio
@pytest.mark.skipif(not qdrant_available(), reason="Qdrant not available")
async def test_search_flow(tmp_path):
    # create tiny git repo
    import subprocess, textwrap, shutil
    repo = tmp_path/"repo"; repo.mkdir()
    subprocess.run(["git","init"], cwd=repo, check=True)
    (repo/"hello.py").write_text("def greet():\n    print('hi')\n")
    subprocess.run(["git","add","."], cwd=repo, check=True)
    subprocess.run(["git","config","user.email","test@example.com"], cwd=repo, check=True)
    subprocess.run(["git","config","user.name","Test User"], cwd=repo, check=True)
    subprocess.run(["git","commit","-m","init"], cwd=repo, check=True)
    sha = subprocess.check_output(["git","rev-parse","HEAD"], cwd=repo,text=True).strip()
    # ingest
    ingest_git_commit(sha, repo)
    async with httpx.AsyncClient(base_url="http://localhost:8000") as c:
        r = await c.get("/search", params={"q":"greet", "k":3})
        assert r.json()["results"]