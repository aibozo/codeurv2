from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from .models import Symbol, SQLModel
from sqlalchemy.ext.asyncio import create_async_engine

from os import getenv
DATABASE_URL = getenv("DATABASE_URL", "postgresql+asyncpg://sr:srpass@localhost:5432/symbol_registry")

engine = create_async_engine(DATABASE_URL, isolation_level="SERIALIZABLE")
async_session = asynccontextmanager(lambda: AsyncSession(engine))

async def reserve(data):
    async with async_session() as session:
        expire = datetime.utcnow() + timedelta(seconds=data.ttl_sec)
        sym = Symbol(**data.model_dump(), reserved_until=expire)
        session.add(sym)
        try:
            await session.commit()
            await session.refresh(sym)
        except Exception:
            await session.rollback()
            raise
        return sym

async def claim(lease_id: int, commit_sha: str):
    async with async_session() as session:
        stmt = select(Symbol).where(Symbol.id == lease_id)
        result = await session.execute(stmt)
        sym = result.scalar_one_or_none()
        if not sym:
            raise ValueError("Lease not found")
        if sym.status != "reserved":
            raise ValueError("Lease not in reserved state")
        if datetime.utcnow() > sym.reserved_until:
            raise ValueError("Lease expired")
        
        sym.status = "active"
        sym.commit_sha = commit_sha
        sym.reserved_until = None
        
        try:
            await session.commit()
            await session.refresh(sym)
        except Exception:
            await session.rollback()
            raise
        return sym

async def lookup(repo: str, branch: str, fq_name: str):
    async with async_session() as session:
        stmt = select(Symbol).where(
            Symbol.repo == repo,
            Symbol.branch == branch,
            Symbol.fq_name == fq_name
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()