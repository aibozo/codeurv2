import grpc
from concurrent import futures
import asyncio
import logging
from pathlib import Path
import pygit2

# We'll generate these from proto file
from proto import git_adapter_pb2
from proto import git_adapter_pb2_grpc

from .server import _ensure_mirror, _checkout

log = logging.getLogger("git-adapter-grpc")

class GitAdapterService(git_adapter_pb2_grpc.GitAdapterServicer):
    def Checkout(self, request, context):
        try:
            repo = _ensure_mirror(request.repo.url)
            wd, sha = _checkout(repo, request.ref)
            return git_adapter_pb2.CheckoutReply(
                workdir=str(wd), 
                commit_sha=sha
            )
        except Exception as e:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            return git_adapter_pb2.CheckoutReply()
    
    def ReadFile(self, request, context):
        try:
            repo = _ensure_mirror(request.repo.url)
            blob = repo.revparse_single(f"{request.ref}:{request.path}")
            if blob.type != pygit2.GIT_OBJ_BLOB:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"{request.path} is not a file")
                return git_adapter_pb2.ReadFileReply()
            return git_adapter_pb2.ReadFileReply(content=blob.data)
        except KeyError:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"File {request.path} not found at {request.ref}")
            return git_adapter_pb2.ReadFileReply()
        except Exception as e:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            return git_adapter_pb2.ReadFileReply()
    
    def Diff(self, request, context):
        try:
            repo = _ensure_mirror(request.repo.url)
            base_commit = repo.revparse_single(request.base)
            head_commit = repo.revparse_single(request.head)
            
            diff = repo.diff(base_commit, head_commit)
            unified_diff = diff.patch
            
            return git_adapter_pb2.DiffReply(unified_diff=unified_diff)
        except Exception as e:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            return git_adapter_pb2.DiffReply()
    
    def Blame(self, request, context):
        try:
            repo = _ensure_mirror(request.repo.url)
            commit = repo.revparse_single(request.ref)
            
            blame_data = repo.blame(request.path, newest_commit=commit.id)
            commits = []
            
            for hunk in blame_data:
                for line in hunk.lines:
                    commits.append(str(hunk.final_commit_id))
            
            return git_adapter_pb2.BlameReply(commits=commits)
        except Exception as e:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            return git_adapter_pb2.BlameReply()

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    git_adapter_pb2_grpc.add_GitAdapterServicer_to_server(
        GitAdapterService(), server
    )
    server.add_insecure_port('[::]:8300')
    server.start()
    log.info("gRPC server started on port 8300")
    server.wait_for_termination()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    serve()