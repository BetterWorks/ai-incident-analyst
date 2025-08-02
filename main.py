import argparse
import os
import sys
import datetime
from dotenv import load_dotenv
load_dotenv()
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))
from ingestion.new_relic_fetcher import NewRelicLogFetcher
from preprocessing.preprocessor import LogPreprocessor
from embedding.embedder import LogEmbedder
from vector_db.faiss_db import FaissVectorDB
from llm.llm_processor import LLMProcessor

def run_pipeline(from_time, to_time, batch_size=5, slack=False):
    if from_time and to_time:
        print(f"Fetching logs from New Relic: {from_time} to {to_time}")
        fetcher = NewRelicLogFetcher()
        import re
        base_query = fetcher.nrql_query
        # Remove any existing SINCE ... UNTIL ..., LIMIT ..., and 'hours ago'/'days ago' (with or without a number)
        base_query = re.sub(r"SINCE [^ ]+( UNTIL [^ ]+)?", "", base_query, flags=re.IGNORECASE)
        base_query = re.sub(r"LIMIT \d+", "", base_query, flags=re.IGNORECASE)
        base_query = re.sub(r"(\d+\s*)?(hours|days) ago", "", base_query, flags=re.IGNORECASE)
        base_query = re.sub(r"\s+", " ", base_query).strip()
        nrql_query = f"{base_query} SINCE '{from_time}' UNTIL '{to_time}' LIMIT 1000"
    else:
        print("Fetching logs from New Relic: last 24 hours")
        fetcher = NewRelicLogFetcher()
        nrql_query = fetcher.nrql_query
    try:
        logs = fetcher.fetch_logs(nrql_query=nrql_query)
        if logs is None:
            print("Error: fetch_logs returned None. Raw API response may be malformed.")
            print(f"NRQL used: {nrql_query}")
            if hasattr(fetcher, 'last_response'):
                print(f"Raw API response: {fetcher.last_response}")
            return
        print(f"Fetched {len(logs)} logs from New Relic.")
        if not logs:
            print("No logs fetched. Exiting.")
            print(f"NRQL used: {nrql_query}")
            return
    except Exception as e:
        print(f"Error fetching logs: {e}")
        print(f"NRQL used: {nrql_query}")
        return
    preprocessor = LogPreprocessor()
    cleaned_logs = preprocessor.preprocess_logs(logs)
    print(f"Preprocessed logs: {len(cleaned_logs)} remain after cleaning/dedup.")
    embedder = LogEmbedder()
    embedded_logs = embedder.embed_logs(cleaned_logs)
    print(f"Embedded {len(embedded_logs)} logs.")
    db = FaissVectorDB()
    db.add_logs(embedded_logs)
    print("Logs added to FAISS vector DB.")
    processor = LLMProcessor(slack_enabled=slack)
    result = processor.process_batch(embedded_logs[:batch_size])
    print("\n=== RCA & Fix Suggestion ===\n")
    print(result["llm_output"])
    print("\n=== Similar Logs (RAG Context) ===\n")
    for log in result["similar_logs"]:
        print(f"- {log.get('timestamp', '')} | {log.get('container_name', '')} | {log.get('level', '')} | {log.get('message', '')}")

    # --- Persist RCA result to dashboard history ---
    import json
    from datetime import datetime as dt
    history_path = os.getenv("DASHBOARD_HISTORY_PATH", "rca_history.json")
    try:
        if os.path.exists(history_path):
            with open(history_path, "r") as f:
                history = json.load(f)
        else:
            history = []
    except Exception as e:
        print(f"Warning: Could not load dashboard history: {e}")
        history = []
    # Use the first log in the batch for top-level metadata
    meta_log = cleaned_logs[0] if cleaned_logs else {}
    entry = {
        "timestamp": meta_log.get("timestamp", dt.utcnow().isoformat()),
        "container_name": meta_log.get("container_name", ""),
        "level": meta_log.get("level", ""),
        "llm_output": result["llm_output"],
        "batch_logs": cleaned_logs[:batch_size],
        "similar_logs": result["similar_logs"]
    }
    history.append(entry)
    try:
        with open(history_path, "w") as f:
            json.dump(history, f, indent=2)
        print(f"Saved RCA result to {history_path} (dashboard will update on refresh)")
    except Exception as e:
        print(f"Warning: Could not save dashboard history: {e}")

def main():
    parser = argparse.ArgumentParser(description="Run AI Debug Agent pipeline on New Relic logs.")
    parser.add_argument('--from', dest='from_time', type=str, help='Start time (ISO8601, default: 1 hour ago)')
    parser.add_argument('--to', dest='to_time', type=str, help='End time (ISO8601, default: now)')
    parser.add_argument('--batch-size', type=int, default=5, help='Number of logs to process in LLM batch')
    parser.add_argument('--slack', action='store_true', help='Send results to Slack')
    args = parser.parse_args()
    if args.from_time and args.to_time:
        # Format as 'YYYY-MM-DD HH:MM:SS' (no T, no microseconds, no Z)
        def nrql_time(dt):
            return dt.replace(microsecond=0).strftime('%Y-%m-%d %H:%M:%S')
        end = datetime.datetime.fromisoformat(args.to_time)
        start = datetime.datetime.fromisoformat(args.from_time)
        run_pipeline(nrql_time(start), nrql_time(end), batch_size=args.batch_size, slack=args.slack)
    else:
        run_pipeline(None, None, batch_size=args.batch_size, slack=args.slack)

if __name__ == "__main__":
    main()
