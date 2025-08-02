import os
import sys
import pytest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from llm.llm_processor import LLMProcessor
from embedding.embedder import LogEmbedder
from preprocessing.preprocessor import LogPreprocessor

# Integration test: embedding → vector DB → LLM (RAG) → Slack



def test_llm_to_slack():
    # Dummy SlackNotifier to capture messages
    sent_messages = []
    class DummySlackNotifier:
        def __init__(self, *args, **kwargs):
            pass
        def send_message(self, text, blocks=None):
            sent_messages.append(text)
            return True

    # Sample raw logs
    raw_logs = [
        {"message": "Service Y crashed due to OOM", "timestamp": "2025-07-25T12:00:00Z", "container_name": "svc-oom", "level": "error"},
        {"message": "Restarted service Y after OOM", "timestamp": "2025-07-25T12:05:00Z", "container_name": "svc-oom", "level": "info"}
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

    # LLM processor with Slack enabled and dummy notifier injected
    processor = LLMProcessor(slack_enabled=True, slack_notifier=DummySlackNotifier())
    result = processor.process_batch(embedded_logs)
    assert "llm_output" in result
    assert isinstance(result["llm_output"], str)
    assert len(result["llm_output"]) > 0
    # Check that a Slack message was sent
    assert sent_messages, "No Slack message was sent!"
    print("Slack message sent:\n", sent_messages[0])

if __name__ == "__main__":
    pytest.main([__file__, "-s"])
