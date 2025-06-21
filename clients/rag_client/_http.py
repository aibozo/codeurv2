import os, httpx, tenacity, logging, json, time
from .typing import DocHit
from .cache import CACHE
from typing import List
from prometheus_client import Counter

BASE = os.getenv("RAG_ENDPOINT", "http://rag_service:8000")
log  = logging.getLogger("rag-client.http")

CALLS = Counter("rag_client_calls_total","calls",["method"])
LAT   = Counter("rag_client_latency_sec","seconds",["method"])

@tenacity.retry(
    wait=tenacity.wait_exponential(multiplier=0.5, min=1, max=8),
    stop=tenacity.stop_after_attempt(3),
    reraise=True)
async def _get(path, params=None):
    async with httpx.AsyncClient(timeout=30) as cli:
        r = await cli.get(f"{BASE}{path}", params=params)
        r.raise_for_status(); return r.json()

async def _timed(fn, *a, **kw):
    t=time.perf_counter()
    res=await fn(*a,**kw)
    LAT.labels(fn.__name__).inc(time.perf_counter()-t)
    return res

async def _hybrid_search_impl(query:str, k:int=8, alpha:float=0.25, filter:dict|None=None) -> List[DocHit]:
    cache_key = f"hs::{query}:{k}:{alpha}:{json.dumps(filter,sort_keys=True) if filter else ''}"
    if hit:=CACHE.get(cache_key): return hit
    params = {"q": query, "k": k, "alpha": alpha}
    if filter: params.update(filter)
    js = await _get("/search", params=params)
    CACHE.set(cache_key, js["results"])
    return js["results"]

async def hybrid_search(query:str, k:int=8, alpha:float=0.25, filter:dict|None=None) -> List[DocHit]:
    CALLS.labels("search").inc()
    return await _timed(_hybrid_search_impl, query, k, alpha, filter)

async def _snippet_impl(point_id:int, radius:int=20)->str:
    cache_key = f"snip::{point_id}:{radius}"
    if hit:=CACHE.get(cache_key): return hit
    js = await _get(f"/snippet/{point_id}", params={"radius": radius})
    CACHE.set(cache_key, js["text"])
    return js["text"]

async def snippet(point_id:int, radius:int=20)->str:
    CALLS.labels("snippet").inc()
    return await _timed(_snippet_impl, point_id, radius)

async def _grep_like_impl(regex:str, repo:str|None=None, k:int=20):
    params={"q":regex,"k":k,"alpha":0.0}
    if repo: params["repo"]=repo
    return await _get("/search", params=params)

async def grep_like(regex:str, repo:str|None=None, k:int=20):
    CALLS.labels("grep").inc()
    return await _timed(_grep_like_impl, regex, repo, k)

async def snippet_stream(ids:list[int], radius:int=30):
    for pid in ids:
        yield await snippet(pid, radius=radius)