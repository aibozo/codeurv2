import os
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

def embed(texts):
    if isinstance(texts, str):
        texts = [texts]
    
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