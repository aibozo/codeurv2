import asyncio
import pytest
import httpx
import os
import time
from sqlalchemy import text
from apps.symbol_registry.models import SQLModel
from apps.symbol_registry.db import engine

@pytest.fixture(scope="session", autouse=True)
async def prepare_db():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)

@pytest.mark.asyncio
async def test_reserve_then_lookup():
    async with httpx.AsyncClient(base_url="http://localhost:8080") as c:
        r = await c.post("/reserve", json={
            "repo": "demo",
            "branch": "main",
            "fq_name": "demo.func",
            "kind": "function",
            "file_path": "demo.py",
            "plan_id": "P1"
        })
        assert r.status_code == 200
        lid = r.json()["lease_id"]
        assert lid is not None
        
        lk = await c.get("/lookup", params={
            "repo": "demo",
            "branch": "main",
            "fq_name": "demo.func"
        })
        assert lk.status_code == 200
        assert lk.json()["status"] == "reserved"

@pytest.mark.asyncio
async def test_claim():
    async with httpx.AsyncClient(base_url="http://localhost:8080") as c:
        # First reserve
        r = await c.post("/reserve", json={
            "repo": "demo2",
            "branch": "main",
            "fq_name": "demo2.func",
            "kind": "function",
            "file_path": "demo2.py",
            "plan_id": "P2"
        })
        assert r.status_code == 200
        lid = r.json()["lease_id"]
        
        # Then claim
        claim_r = await c.post("/claim", json={
            "lease_id": lid,
            "commit_sha": "abc123"
        })
        assert claim_r.status_code == 200
        assert claim_r.json()["status"] == "active"
        
        # Verify lookup shows active
        lk = await c.get("/lookup", params={
            "repo": "demo2",
            "branch": "main",
            "fq_name": "demo2.func"
        })
        assert lk.status_code == 200
        assert lk.json()["status"] == "active"
        assert lk.json()["commit_sha"] == "abc123"

@pytest.mark.asyncio
async def test_health():
    async with httpx.AsyncClient(base_url="http://localhost:8080") as c:
        r = await c.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"