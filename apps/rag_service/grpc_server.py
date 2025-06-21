import grpc
import asyncio
from concurrent import futures
import sys
sys.path.append('.')
from proto import rag_pb2, rag_pb2_grpc
from .api import http_search, http_snippet

class RagServiceServicer(rag_pb2_grpc.RagServiceServicer):
    async def HybridSearch(self, request, context):
        try:
            # Call the same logic as HTTP endpoint
            result = await http_search(request.query, request.k, request.alpha)
            reply = rag_pb2.SearchReply()
            for r in result["results"]:
                doc_ref = rag_pb2.DocRef()
                doc_ref.point_id = str(r["point_id"])
                doc_ref.snippet = r["snippet"]
                doc_ref.score = 0.0  # Score not exposed in HTTP response
                reply.results.append(doc_ref)
            return reply
        except Exception as e:
            context.abort(grpc.StatusCode.INTERNAL, str(e))
    
    async def Snippet(self, request, context):
        try:
            # Convert string point_id to int
            pid = int(request.point_id)
            result = await http_snippet(pid, request.radius)
            return rag_pb2.SnippetReply(text=result["text"])
        except Exception as e:
            context.abort(grpc.StatusCode.INTERNAL, str(e))

async def serve():
    server = grpc.aio.server()
    rag_pb2_grpc.add_RagServiceServicer_to_server(RagServiceServicer(), server)
    server.add_insecure_port('[::]:9100')
    await server.start()
    await server.wait_for_termination()