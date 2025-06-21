import asyncio, uvicorn
from .api import app
from .grpc_server import serve

async def start():
    asyncio.create_task(serve())
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    asyncio.run(start())