#!/usr/bin/env python3
"""Initialize database tables for Symbol Registry"""
import asyncio
import sys
sys.path.insert(0, '/home/kil/dev/codeur')

from apps.symbol_registry.models import SQLModel
from apps.symbol_registry.db import engine

async def init_db():
    print("Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    print("Tables created successfully!")

if __name__ == "__main__":
    asyncio.run(init_db())