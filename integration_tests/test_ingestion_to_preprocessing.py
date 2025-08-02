import sys
import os
import pytest
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from ingestion.new_relic_fetcher import NewRelicLogFetcher
from preprocessing.preprocessor import LogPreprocessor

def test_ingestion_to_preprocessing():
    fetcher = NewRelicLogFetcher()
    logs = fetcher.fetch_logs(debug=False)
    assert isinstance(logs, list)
    assert all(isinstance(log, dict) for log in logs)
    pre = LogPreprocessor()
    cleaned = pre.preprocess_logs(logs)
    assert isinstance(cleaned, list)
    # Optionally, check that cleaned logs are a subset or equal in length
    assert len(cleaned) <= len(logs)
    # Optionally, print for debug
    print(f"Fetched {len(logs)} logs from New Relic. After preprocessing: {len(cleaned)} logs remain.")
    for log in cleaned[:3]:
        print(log)
