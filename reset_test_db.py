#!/usr/bin/env python
"""Reset test databases before running tests"""
import asyncio
import asyncpg
import os

async def reset_postgres():
    """Drop and recreate the symbol_registry database"""
    try:
        # Connect to postgres default database
        conn = await asyncpg.connect(
            host='localhost',
            port=5433,
            user='sr',
            password='srpass',
            database='postgres'
        )
        
        # Drop and recreate database
        await conn.execute("DROP DATABASE IF EXISTS symbol_registry")
        await conn.execute("CREATE DATABASE symbol_registry")
        await conn.close()
        print("✓ PostgreSQL database reset")
    except Exception as e:
        print(f"✗ PostgreSQL reset failed: {e}")

def reset_qdrant():
    """Clear Qdrant collections"""
    try:
        import qdrant_client
        client = qdrant_client.QdrantClient(url="http://localhost:6333")
        collections = client.get_collections().collections
        for collection in collections:
            client.delete_collection(collection.name)
            print(f"✓ Deleted Qdrant collection: {collection.name}")
    except Exception as e:
        print(f"✗ Qdrant reset failed: {e}")

def reset_sqlite():
    """Remove SQLite database file"""
    try:
        if os.path.exists("bm25.db"):
            os.remove("bm25.db")
            print("✓ SQLite database removed")
    except Exception as e:
        print(f"✗ SQLite reset failed: {e}")

async def main():
    print("Resetting test databases...")
    await reset_postgres()
    reset_qdrant()
    reset_sqlite()
    print("\nDatabases reset. You can now run: poetry run pytest")

if __name__ == "__main__":
    asyncio.run(main())