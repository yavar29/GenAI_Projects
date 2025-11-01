import numpy as np
from openai import OpenAI
from app.config.settings import EMBED_MODEL

_client = OpenAI()

def embed_texts(texts: list[str]) -> np.ndarray:
    # OpenAI returns a list of vectors; convert to np.array
    resp = _client.embeddings.create(model=EMBED_MODEL, input=texts)
    vecs = [d.embedding for d in resp.data]
    return np.array(vecs, dtype=np.float32)
