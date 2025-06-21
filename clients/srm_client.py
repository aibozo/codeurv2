import grpclib
from grpclib.client import Channel
from apps.symbol_registry import symbol_pb2, symbol_grpc

class SRMClient:
    def __init__(self, target="localhost", port=9090):
        self._channel = Channel(target, port)
        self._stub = symbol_grpc.SymbolRegistryStub(self._channel)
    
    async def reserve(self, **kw):
        reply = await self._stub.Reserve(symbol_pb2.ReserveRequest(**kw))
        return reply
    
    async def claim(self, lease_id: int, commit_sha: str):
        reply = await self._stub.Claim(symbol_pb2.ClaimRequest(
            lease_id=lease_id,
            commit_sha=commit_sha
        ))
        return reply
    
    async def lookup(self, repo: str, branch: str, fq_name: str):
        reply = await self._stub.Lookup(symbol_pb2.LookupRequest(
            repo=repo,
            branch=branch,
            fq_name=fq_name
        ))
        return reply
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *exc):
        self._channel.close()