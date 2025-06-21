import os, qdrant_client, numpy as np
from qdrant_client.http import models as qmodels

COLL = "code_chunks"
# OpenAI text-embedding-3-small has 1536 dimensions, BGE has 768
DIM = 1536 if os.getenv("EMBEDDING_BACKEND") == "openai" else 768
client = qdrant_client.QdrantClient(url=os.getenv("QDRANT_URL","http://localhost:6333"))

def ensure_collection():
    if COLL not in [c.name for c in client.get_collections().collections]:
        client.create_collection(
            collection_name=COLL,
            vectors_config=qmodels.VectorParams(size=DIM, distance="Cosine")
        )
ensure_collection()

def upsert_vectors(ids, vectors, payloads):
    client.upsert(COLL, points=[
        qmodels.PointStruct(id=i, vector=v, payload=p)
        for i, v, p in zip(ids, vectors, payloads)
    ])

def search_dense(query_vec, k):
    hits = client.search(COLL, query_vector=query_vec, limit=k)
    return hits  # id, score