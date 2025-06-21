from fastapi import FastAPI, HTTPException, Query
from .vector import search_dense
from .bm25 import bm25_search, db
from .embedding import embed
from prometheus_client import make_asgi_app, Counter

app = FastAPI(title="RAG Service")
SEARCH_QPS = Counter("rag_search_total","search calls")

@app.get("/search")
async def http_search(q: str = Query(...), k: int = 8, alpha: float = 0.25):
    SEARCH_QPS.inc()
    dense = search_dense(embed([q])[0], k*2)
    sparse = bm25_search(q, k*2)
    # fuse
    scores = {}
    for p in dense: scores[p.id] = alpha * p.score
    for row in sparse:
        scores[row["point_id"]] = scores.get(row["point_id"],0) + (1-alpha)/row["score"]
    top = sorted(scores.items(), key=lambda x: -x[1])[:k]
    results = []
    for pid,_ in top:
        snippet = db["fts"].get(pid)["content"][:200]
        results.append({"point_id": pid, "snippet": snippet})
    return {"results": results}

@app.get("/snippet/{point_id}")
async def http_snippet(point_id: int, radius: int = 20):
    rec = db["fts"].get(point_id)
    return {"text": rec["content"][:radius*10]}

app.mount("/metrics", make_asgi_app())