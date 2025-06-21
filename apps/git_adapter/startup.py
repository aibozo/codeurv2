import asyncio
import logging
import threading
import uvicorn
from .server import app
from .grpc_server import serve

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger("git-adapter")

async def start_http():
    """Start the FastAPI HTTP server"""
    config = uvicorn.Config(
        app, 
        host="0.0.0.0", 
        port=8200,
        log_level="info"
    )
    server = uvicorn.Server(config)
    await server.serve()

def start_grpc_thread():
    """Start the gRPC server in a separate thread"""
    serve()

async def main():
    """Run both HTTP and gRPC servers concurrently"""
    log.info("Starting Git Adapter service...")
    
    # Start gRPC in a thread since it's not async
    grpc_thread = threading.Thread(target=start_grpc_thread, daemon=True)
    grpc_thread.start()
    
    # Start HTTP server
    await start_http()

if __name__ == "__main__":
    asyncio.run(main())