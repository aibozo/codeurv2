import os
import hashlib
import numpy as np
from sentence_transformers import SentenceTransformer

EMBEDDING_BACKEND = os.getenv("EMBEDDING_BACKEND", "sentence_transformers")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-code-v1.5")

print(f"DEBUG: EMBEDDING_BACKEND = {EMBEDDING_BACKEND}")
print(f"DEBUG: EMBEDDING_MODEL = {EMBEDDING_MODEL}")

_model = None
_openai_client = None

def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        import openai
        _openai_client = openai.OpenAI()
    return _openai_client

def _get_sentence_transformer():
    global _model
    if _model is None:
        if EMBEDDING_BACKEND == "openai":
            raise ValueError("Cannot use SentenceTransformer with OpenAI backend")
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model

def _dummy_embed(texts: list[str], dim: int = 768) -> list[list[float]]:
    """Fallback embedding using deterministic hash-based vectors"""
    vecs = []
    for t in texts:
        h = hashlib.md5(t.encode()).digest()
        # deterministic pseudo-vector; first 16 bytes mapped to [0,1], rest zeros
        v = np.zeros(dim, dtype=np.float32)
        v[:len(h)] = np.frombuffer(h, dtype=np.uint8) / 255.0
        vecs.append(v.tolist())
    return vecs

def embed(texts):
    if isinstance(texts, str):
        texts = [texts]
    
    try:
        if EMBEDDING_BACKEND == "openai":
            client = _get_openai_client()
            response = client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=texts
            )
            return [item.embedding for item in response.data]
        else:
            model = _get_sentence_transformer()
            return model.encode(texts, normalize_embeddings=True).tolist()
    except Exception as e:
        print(f"[embedding] fallback due to error: {e}")
        # Use appropriate dimension based on backend
        dim = 1536 if EMBEDDING_BACKEND == "openai" else 768
        return _dummy_embed(texts, dim)