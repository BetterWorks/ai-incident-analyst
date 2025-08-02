
import requests
from src.config import get_config
from typing import List, Dict, Any
from logging_utils.logger import setup_logger
from vector_db.faiss_db import FaissVectorDB
from slack_integration.slack_notifier import SlackNotifier

class LLMProcessor:
    def __init__(self, ollama_url=None, model=None, rag_k=None, slack_enabled=None, slack_notifier=None):
        self.logger = setup_logger()
        self.ollama_url = ollama_url or get_config("OLLAMA_URL", default="http://localhost:11434/api/generate")
        self.model = model or get_config("LLM_MODEL", default="llama3")
        self.rag_k = int(rag_k or get_config("RAG_TOP_K", default=5))
        self.db = FaissVectorDB()
        self.slack_enabled = slack_enabled if slack_enabled is not None else get_config("SLACK_NOTIFY", default="false").lower() == "true"
        if slack_notifier is not None:
            self.slack_notifier = slack_notifier
        elif self.slack_enabled:
            try:
                self.slack_notifier = SlackNotifier()
                self.logger.info("Slack integration enabled for LLMProcessor.")
            except Exception as e:
                self.logger.error(f"SlackNotifier init failed: {e}")
                self.slack_enabled = False
        else:
            self.slack_notifier = None
        self.logger.info(f"LLMProcessor initialized with model {self.model}, RAG top-k {self.rag_k}")

    def build_prompt(self, batch_logs: List[Dict], similar_logs: List[Dict]) -> str:
        prompt = """
Given the following logs and similar past incidents, summarize the root cause and suggest a fix.

Current Logs:
"""
        for log in batch_logs:
            prompt += f"- {log.get('timestamp', '')} | {log.get('container_name', '')} | {log.get('level', '')} | {self._redact(log.get('message', ''))}\n"
        prompt += "\nSimilar Past Incidents:\n"
        for log in similar_logs:
            prompt += f"- {log.get('timestamp', '')} | {log.get('container_name', '')} | {log.get('level', '')} | {self._redact(log.get('message', ''))}\n"
        prompt += "\nRCA and Fix Suggestion:"
        return prompt

    def get_similar_logs(self, logs: List[Dict]) -> List[Dict]:
        # Use the first log's embedding for RAG context (can be improved to use all)
        if not logs or "embedding" not in logs[0]:
            return []
        all_similar = []
        for log in logs:
            if "embedding" in log:
                similar = self.db.search(log["embedding"], k=self.rag_k)
                all_similar.extend(similar)
        # Deduplicate by message/timestamp
        seen = set()
        deduped = []
        for log in all_similar:
            key = (log.get("timestamp"), log.get("message"))
            if key not in seen:
                seen.add(key)
                deduped.append(log)
        return deduped

    def call_ollama(self, prompt: str, max_retries: int = 3) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }
        for attempt in range(1, max_retries + 1):
            try:
                response = requests.post(self.ollama_url, json=payload, timeout=60)
                response.raise_for_status()
                result = response.json()
                return result.get("response", "")
            except Exception as e:
                self.logger.error(f"Ollama LLM call failed (attempt {attempt}): {e}")
                if attempt == max_retries:
                    return "LLM processing failed."

    def process_batch(self, batch_logs: List[Dict]) -> Dict[str, Any]:
        self.logger.info(f"Processing batch of {len(batch_logs)} logs with LLM...")
        similar_logs = self.get_similar_logs(batch_logs)
        prompt = self.build_prompt(batch_logs, similar_logs)
        self.logger.info(f"LLM prompt (redacted):\n{self._redact(prompt)}")
        llm_output = self.call_ollama(prompt)
        self.logger.info(f"LLM output: {self._redact(llm_output)}")
        if self.slack_enabled and self.slack_notifier:
            slack_msg = self._format_slack_message(batch_logs, llm_output)
            self.slack_notifier.send_message(slack_msg)
        self.logger.info("LLM processing complete.")
        return {
            "prompt": prompt,
            "llm_output": llm_output,
            "similar_logs": similar_logs
        }

    def _format_slack_message(self, batch_logs, llm_output):
        # Simple formatting: show RCA/fix, and a summary of the logs
        log_lines = [f"- {log.get('timestamp', '')} | {log.get('container_name', '')} | {log.get('level', '')} | {self._redact(log.get('message', ''))}" for log in batch_logs]
        msg = (
            "*AI RCA & Fix Suggestion:*\n"
            "*Logs:*\n" + '\n'.join(log_lines) +
            "\n*RCA & Fix:*\n" + self._redact(llm_output)
        )
        return msg
    def _redact(self, text: str) -> str:
        # Simple redaction for secrets, emails, tokens, etc. (customize as needed)
        import re
        text = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+", "[REDACTED_EMAIL]", text)
        text = re.sub(r"(?i)api[_-]?key\s*[:=]\s*\w+", "api_key=[REDACTED]", text)
        text = re.sub(r"(?i)token\s*[:=]\s*\w+", "token=[REDACTED]", text)
        return text

if __name__ == "__main__":
    # Example usage
    logs = [
        {"message": "Service crashed with OOM", "timestamp": "2025-07-25T00:00:00Z", "container_name": "svc1", "level": "error", "embedding": [0.1]*384}
    ]
    processor = LLMProcessor()
    result = processor.process_batch(logs)
    print(result["llm_output"])
