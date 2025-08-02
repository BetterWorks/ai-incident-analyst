import os
import sys
import pytest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from llm.llm_processor import LLMProcessor
from embedding.embedder import LogEmbedder
from preprocessing.preprocessor import LogPreprocessor

# Integration test: embedding → vector DB → LLM (RAG)
def test_llm_processor_end_to_end():
    # Sample raw logs
    raw_logs = [
        {"message": "Database connection timeout on service X", "timestamp": "2025-07-25T10:00:00Z", "container_name": "svc-db", "level": "error"},
        {"message": "Service X restarted after OOM", "timestamp": "2025-07-25T10:05:00Z", "container_name": "svc-db", "level": "warning"}
    ]
    # Preprocess
    preprocessor = LogPreprocessor()
    cleaned_logs = preprocessor.preprocess_logs(raw_logs)
    # Embed
    embedder = LogEmbedder()
    embedded_logs = embedder.embed_logs(cleaned_logs)
    # Store in vector DB
    from vector_db.faiss_db import FaissVectorDB
    db = FaissVectorDB()
    db.add_logs(embedded_logs)
    # LLM processor
    processor = LLMProcessor()
    result = processor.process_batch(embedded_logs)
    assert "llm_output" in result
    assert isinstance(result["llm_output"], str)
    assert len(result["llm_output"]) > 0
    print("LLM Output:\n", result["llm_output"])

if __name__ == "__main__":
    test_llm_processor_end_to_end()
