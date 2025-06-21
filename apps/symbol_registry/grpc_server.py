import grpclib
from grpclib.server import Server
from grpclib.utils import graceful_exit
from . import symbol_pb2, symbol_grpc
from .db import reserve, claim, lookup
from pydantic import BaseModel

class ReserveData(BaseModel):
    repo: str
    branch: str
    fq_name: str
    kind: str
    file_path: str
    plan_id: str
    ttl_sec: int

class SRM(symbol_grpc.SymbolRegistryBase):
    async def Reserve(self, stream):
        req = await stream.recv_message()
        data = ReserveData(
            repo=req.repo,
            branch=req.branch,
            fq_name=req.fq_name,
            kind=req.kind,
            file_path=req.file_path,
            plan_id=req.plan_id,
            ttl_sec=req.ttl_sec
        )
        try:
            rec = await reserve(data)
            await stream.send_message(symbol_pb2.ReserveReply(
                lease_id=rec.id,
                status=rec.status,
                expires_at=rec.reserved_until.isoformat()
            ))
        except Exception:
            await stream.send_message(symbol_pb2.ReserveReply(
                lease_id=0,
                status="error",
                expires_at=""
            ))
    
    async def Claim(self, stream):
        req = await stream.recv_message()
        try:
            rec = await claim(req.lease_id, req.commit_sha)
            await stream.send_message(symbol_pb2.ClaimReply(
                status=rec.status
            ))
        except Exception as e:
            await stream.send_message(symbol_pb2.ClaimReply(
                status=f"error: {str(e)}"
            ))
    
    async def Lookup(self, stream):
        req = await stream.recv_message()
        rec = await lookup(req.repo, req.branch, req.fq_name)
        if rec:
            await stream.send_message(symbol_pb2.LookupReply(
                status=rec.status,
                file_path=rec.file_path,
                commit_sha=rec.commit_sha or ""
            ))
        else:
            await stream.send_message(symbol_pb2.LookupReply(
                status="not_found",
                file_path="",
                commit_sha=""
            ))

async def serve():
    server = Server([SRM()])
    with graceful_exit([server]):
        await server.start(host="0.0.0.0", port=9090)
        await server.wait_closed()