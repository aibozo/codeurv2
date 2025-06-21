import aiohttp, os, json, asyncio
BASE = os.getenv("GIT_ADAPTER_ENDPOINT", "http://git_adapter:8200")

async def checkout(repo_url: str, ref: str) -> dict:
    """Checkout a repository at a specific ref and return workdir and commit SHA"""
    body = {"repo": {"url": repo_url}, "ref": ref}
    async with aiohttp.ClientSession() as s:
        r = await s.post(f"{BASE}/checkout", json=body, timeout=60)
        r.raise_for_status()
        return await r.json()

async def read_file(repo_url: str, ref: str, path: str) -> bytes:
    """Read a file from a repository at a specific ref"""
    params = {"repo_url": repo_url, "ref": ref, "path": path}
    async with aiohttp.ClientSession() as s:
        r = await s.get(f"{BASE}/read_file", params=params, timeout=60)
        r.raise_for_status()
        return await r.read()

async def diff(repo_url: str, base: str, head: str) -> str:
    """Get unified diff between two commits/refs"""
    params = {"repo_url": repo_url, "base": base, "head": head}
    async with aiohttp.ClientSession() as s:
        r = await s.get(f"{BASE}/diff", params=params, timeout=60)
        r.raise_for_status()
        data = await r.json()
        return data["unified_diff"]

async def blame(repo_url: str, ref: str, path: str) -> list[str]:
    """Get blame information for a file, returns list of commit SHAs per line"""
    params = {"repo_url": repo_url, "ref": ref, "path": path}
    async with aiohttp.ClientSession() as s:
        r = await s.get(f"{BASE}/blame", params=params, timeout=60)
        r.raise_for_status()
        data = await r.json()
        return data["commits"]

async def health() -> dict:
    """Check health of git adapter service"""
    async with aiohttp.ClientSession() as s:
        r = await s.get(f"{BASE}/health", timeout=10)
        r.raise_for_status()
        return await r.json()