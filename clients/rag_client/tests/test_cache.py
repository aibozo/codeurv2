import asyncio, pytest
from clients.rag_client import hybrid_search

@pytest.mark.asyncio
async def test_hybrid_cache(monkeypatch):
    calls=0
    async def fake_get(*_,**__):
        nonlocal calls; calls+=1
        return {"results":[{"point_id":1,"snippet":"hi","score":1.0}]}
    monkeypatch.setattr("clients.rag_client._http._get", fake_get)
    res1=await hybrid_search("hello",k=2)
    res2=await hybrid_search("hello",k=2)
    assert calls==1 and res1==res2