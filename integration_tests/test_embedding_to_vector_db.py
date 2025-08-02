import sys
import os
import pytest
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from preprocessing.preprocessor import LogPreprocessor
from embedding.embedder import LogEmbedder
from vector_db.faiss_db import FaissVectorDB

def test_embedding_to_vector_db():
    logs = [
        {"message": "User john.doe@email.com logged in", "timestamp": 123456, "event": "login"},
        {"message": "Payment with card 4111 1111 1111 1111", "timestamp": 123457, "event": "payment"},
        {"message": None, "timestamp": 123458, "event": "other"}
    ]
    pre = LogPreprocessor()
    cleaned = pre.preprocess_logs(logs)
    assert isinstance(cleaned, list)
    embedder = LogEmbedder(fields_to_embed=["message", "event"])
    logs_with_emb = embedder.embed_logs(cleaned)
    assert isinstance(logs_with_emb, list)
    assert all("embedding" in log for log in logs_with_emb)
    db = FaissVectorDB(dim=len(logs_with_emb[0]["embedding"]))
    db.add_logs(logs_with_emb)
    results = db.search(logs_with_emb[0]["embedding"], k=2)
    assert isinstance(results, list)
    print(f"Added logs to FAISS DB. Search results:")
    for res in results:
        print(res)
