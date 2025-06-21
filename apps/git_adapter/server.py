import os, tempfile, shutil, logging, asyncio, hashlib, functools
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pygit2
from prometheus_client import Counter, Histogram, make_asgi_app

CACHE = Path(os.getenv("GIT_CACHE", "/var/git-cache"))
log = logging.getLogger("git-adapter")

def _ensure_cache_dir():
    """Ensure cache directory exists"""
    CACHE.mkdir(parents=True, exist_ok=True)

REQUESTS = Counter("ga_requests_total", "requests", ["rpc"])
LATENCY  = Histogram("ga_latency_sec", "latency", ["rpc"])

def _cache_path(url: str) -> Path:
    h = hashlib.md5(url.encode()).hexdigest()[:12]
    return CACHE / f"{h}.git"

def _ensure_mirror(url: str) -> pygit2.Repository:
    _ensure_cache_dir()  # Ensure cache directory exists
    path = _cache_path(url)
    if not path.exists():
        log.info("mirroring %s", url)
        pygit2.clone_repository(url, str(path), bare=True)
    repo = pygit2.Repository(str(path))
    return repo

def _checkout(repo: pygit2.Repository, ref: str) -> tuple[Path, str]:
    commit = repo.revparse_single(ref)
    work = Path(tempfile.mkdtemp())
    pygit2.clone_repository(repo.path, str(work), checkout_branch=commit.hex)
    return work, commit.hex

app = FastAPI(title="Git Adapter")
app.mount("/metrics", make_asgi_app())

class Repo(BaseModel):
    url: str

class CheckoutRequest(BaseModel):
    repo: Repo
    ref: str

@app.post("/checkout")
async def checkout(body: CheckoutRequest):
    REQUESTS.labels("checkout").inc()
    try:
        repo = _ensure_mirror(body.repo.url)
        wd, sha = _checkout(repo, body.ref)
        return {"workdir": str(wd), "commit_sha": sha}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/read_file")
async def read_file(repo_url: str, ref: str, path: str):
    from fastapi.responses import Response
    import time
    start = time.time()
    REQUESTS.labels("read_file").inc()
    try:
        repo = _ensure_mirror(repo_url)
        blob = repo.revparse_single(f"{ref}:{path}")
        if blob.type != pygit2.GIT_OBJECT_BLOB:
            raise HTTPException(status_code=404, detail=f"{path} is not a file")
        return Response(content=blob.data, media_type="application/octet-stream")
    except KeyError:
        raise HTTPException(status_code=404, detail=f"File {path} not found at {ref}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        LATENCY.labels("read_file").observe(time.time() - start)

@app.get("/diff")
async def diff(repo_url: str, base: str, head: str):
    REQUESTS.labels("diff").inc()
    try:
        repo = _ensure_mirror(repo_url)
        base_commit = repo.revparse_single(base)
        head_commit = repo.revparse_single(head)
        
        # Get diff between commits
        diff = repo.diff(base_commit, head_commit)
        unified_diff = diff.patch
        
        return {"unified_diff": unified_diff}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/blame")
async def blame(repo_url: str, ref: str, path: str):
    REQUESTS.labels("blame").inc()
    try:
        repo = _ensure_mirror(repo_url)
        commit = repo.revparse_single(ref)
        
        # Get blame for file
        blame_data = repo.blame(path, newest_commit=commit.id)
        commits = []
        
        for hunk in blame_data:
            for line in hunk.lines:
                commits.append(str(hunk.final_commit_id))
        
        return {"commits": commits}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "healthy", "cache_dir": str(CACHE)}