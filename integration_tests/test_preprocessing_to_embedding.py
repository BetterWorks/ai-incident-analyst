import sys
import os
import pytest
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from preprocessing.preprocessor import LogPreprocessor
from embedding.embedder import LogEmbedder

def test_preprocessing_to_embedding():
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
    print(f"After preprocessing: {len(cleaned)} logs remain. After embedding: {len(logs_with_emb)} logs with embeddings.")
    for log in logs_with_emb[:3]:
        print({k: v for k, v in log.items() if k != 'embedding'})
        print(f"Embedding (first 5 dims): {log['embedding'][:5]}")
