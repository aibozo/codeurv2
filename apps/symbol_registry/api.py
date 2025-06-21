from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from prometheus_client import Counter, Histogram, make_asgi_app
from .db import reserve, claim, lookup

app = FastAPI(title="Symbol Registry")

REQUESTS = Counter("srm_reserve_total", "reserve calls", ["status"])
LATENCY = Histogram("srm_lookup_latency_ms", "ms", ["repo"])
app.mount("/metrics", make_asgi_app())

class ReserveBody(BaseModel):
    repo: str
    branch: str
    fq_name: str
    kind: str
    file_path: str
    plan_id: str
    ttl_sec: int = 600

class ClaimBody(BaseModel):
    lease_id: int
    commit_sha: str

class LookupParams(BaseModel):
    repo: str
    branch: str
    fq_name: str

@app.post("/reserve")
async def http_reserve(body: ReserveBody):
    try:
        rec = await reserve(body)
        REQUESTS.labels(status="success").inc()
    except Exception:
        REQUESTS.labels(status="conflict").inc()
        raise HTTPException(409, "symbol already exists")
    return {
        "lease_id": rec.id,
        "status": rec.status,
        "expires_at": rec.reserved_until.isoformat()
    }

@app.post("/claim")
async def http_claim(body: ClaimBody):
    try:
        rec = await claim(body.lease_id, body.commit_sha)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception:
        raise HTTPException(500, "internal error")
    return {"status": rec.status}

@app.get("/lookup")
async def http_lookup(repo: str, branch: str, fq_name: str):
    with LATENCY.labels(repo=repo).time():
        rec = await lookup(repo, branch, fq_name)
    
    if not rec:
        raise HTTPException(404, "symbol not found")
    
    return {
        "status": rec.status,
        "file_path": rec.file_path,
        "commit_sha": rec.commit_sha
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}