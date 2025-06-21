import asyncio
import uvicorn
from .api import app
from .grpc_server import serve

async def start_grpc():
    await serve()

async def start_http():
    config = uvicorn.Config(app, host="0.0.0.0", port=8080)
    server = uvicorn.Server(config)
    await server.serve()

async def main():
    await asyncio.gather(
        start_grpc(),
        start_http()
    )

if __name__ == "__main__":
    asyncio.run(main())