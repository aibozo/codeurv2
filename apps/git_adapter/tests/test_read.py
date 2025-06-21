import asyncio, pytest, subprocess, pathlib, textwrap
import tempfile
import shutil
from pathlib import Path
from apps.git_adapter.server import _ensure_mirror, _cache_path

@pytest.fixture
def temp_cache(tmp_path):
    """Temporarily override the cache directory for tests"""
    import apps.git_adapter.server
    original_cache = apps.git_adapter.server.CACHE
    test_cache = tmp_path / "test_cache"
    test_cache.mkdir(exist_ok=True)
    apps.git_adapter.server.CACHE = test_cache
    yield test_cache
    apps.git_adapter.server.CACHE = original_cache

@pytest.mark.asyncio
async def test_mirror_and_read(tmp_path, temp_cache):
    """Test mirroring a local repo and reading files"""
    # Create a test repository
    repo = tmp_path/"repo"
    repo.mkdir()
    (repo/"hello.py").write_text("print('hi')")
    (repo/"README.md").write_text("# Test Repo")
    
    # Initialize git repo
    subprocess.run(["git","init"], cwd=repo, check=True)
    subprocess.run(["git","config","user.email","test@example.com"], cwd=repo, check=True)
    subprocess.run(["git","config","user.name","Test User"], cwd=repo, check=True)
    subprocess.run(["git","add","."], cwd=repo, check=True)
    subprocess.run(["git","commit","-m","init"], cwd=repo, check=True)
    
    # Test mirroring
    r = _ensure_mirror(str(repo))
    assert r is not None
    
    # Verify cache was created
    cache_path = _cache_path(str(repo))
    assert cache_path.exists()
    assert cache_path.is_dir()

@pytest.mark.asyncio
async def test_read_file_from_api(tmp_path, temp_cache):
    """Test reading files through the API endpoints"""
    from apps.git_adapter.server import app
    from httpx import AsyncClient, ASGITransport
    
    # Create test repo
    repo = tmp_path/"test_repo"
    repo.mkdir()
    (repo/"test.txt").write_text("Hello World")
    (repo/"subdir").mkdir()
    (repo/"subdir"/"nested.py").write_text("def hello():\n    return 'Hi'")
    
    subprocess.run(["git","init"], cwd=repo, check=True)
    subprocess.run(["git","config","user.email","test@example.com"], cwd=repo, check=True)
    subprocess.run(["git","config","user.name","Test User"], cwd=repo, check=True)
    subprocess.run(["git","add","."], cwd=repo, check=True)
    subprocess.run(["git","commit","-m","test commit"], cwd=repo, check=True)
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Test reading a file
        response = await client.get("/read_file", params={
            "repo_url": str(repo),
            "ref": "HEAD",
            "path": "test.txt"
        })
        if response.status_code != 200:
            print(f"Error response: {response.json()}")
        assert response.status_code == 200
        assert response.content == b"Hello World"
        
        # Test reading nested file
        response = await client.get("/read_file", params={
            "repo_url": str(repo),
            "ref": "HEAD",
            "path": "subdir/nested.py"
        })
        assert response.status_code == 200
        assert b"def hello" in response.content
        
        # Test file not found
        response = await client.get("/read_file", params={
            "repo_url": str(repo),
            "ref": "HEAD",
            "path": "nonexistent.txt"
        })
        assert response.status_code == 404

@pytest.mark.asyncio
async def test_diff_endpoint(tmp_path, temp_cache):
    """Test the diff endpoint"""
    from apps.git_adapter.server import app
    from httpx import AsyncClient, ASGITransport
    
    # Create test repo with two commits
    repo = tmp_path/"diff_repo"
    repo.mkdir()
    (repo/"file.txt").write_text("Line 1\nLine 2\nLine 3")
    
    subprocess.run(["git","init"], cwd=repo, check=True)
    subprocess.run(["git","config","user.email","test@example.com"], cwd=repo, check=True)
    subprocess.run(["git","config","user.name","Test User"], cwd=repo, check=True)
    subprocess.run(["git","add","."], cwd=repo, check=True)
    subprocess.run(["git","commit","-m","first commit"], cwd=repo, check=True)
    
    # Get first commit SHA
    result = subprocess.run(["git","rev-parse","HEAD"], cwd=repo, capture_output=True, text=True)
    first_commit = result.stdout.strip()
    
    # Make changes
    (repo/"file.txt").write_text("Line 1\nLine 2 modified\nLine 3\nLine 4")
    subprocess.run(["git","add","."], cwd=repo, check=True)
    subprocess.run(["git","commit","-m","second commit"], cwd=repo, check=True)
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/diff", params={
            "repo_url": str(repo),
            "base": first_commit,
            "head": "HEAD"
        })
        assert response.status_code == 200
        data = response.json()
        assert "unified_diff" in data
        assert "-Line 2" in data["unified_diff"]
        assert "+Line 2 modified" in data["unified_diff"]
        assert "+Line 4" in data["unified_diff"]

@pytest.mark.asyncio
async def test_health_endpoint():
    """Test the health check endpoint"""
    from apps.git_adapter.server import app
    from httpx import AsyncClient, ASGITransport
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "cache_dir" in data