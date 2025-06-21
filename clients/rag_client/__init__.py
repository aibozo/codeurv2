import os
from .typing import DocHit
from typing import List

MODE = os.getenv("RAG_CLIENT_TRANSPORT","http")  # http | grpc
if MODE == "grpc":
    from ._grpc import hybrid_search, snippet, grep_like, snippet_stream
else:
    from ._http import hybrid_search, snippet, grep_like, snippet_stream

__all__ = ["hybrid_search", "snippet", "grep_like", "snippet_stream", "DocHit"]