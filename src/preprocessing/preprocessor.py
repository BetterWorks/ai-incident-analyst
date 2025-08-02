import re
from typing import List, Dict
from logging_utils.logger import setup_logger

class LogPreprocessor:
    def __init__(self, redact_patterns=None):
        self.logger = setup_logger()
        # List of (pattern, replacement) tuples for redaction
        self.redact_patterns = redact_patterns or [
            (r"[\w\.-]+@[\w\.-]+", "[REDACTED_EMAIL]"),
            (r"\b(?:\d[ -]*?){13,16}\b", "[REDACTED_CARD]")
        ]
        self.logger.info("LogPreprocessor initialized with %d redact patterns.", len(self.redact_patterns))

    def clean_log(self, log: Dict) -> Dict:
        # Redact sensitive info in message
        msg = log.get("message", "")
        if not isinstance(msg, str):
            msg = str(msg) if msg is not None else ""
        for pattern, repl in self.redact_patterns:
            msg = re.sub(pattern, repl, msg)
        log["message"] = msg
        # Normalize timestamp if present
        if "timestamp" in log:
            log["timestamp"] = str(log["timestamp"])
        self.logger.debug(f"Cleaned log: {log}")
        # Add more cleaning/normalization as needed
        return log

    def preprocess_logs(self, logs: List[Dict]) -> List[Dict]:
        self.logger.info(f"Preprocessing {len(logs)} logs...")
        cleaned = []
        seen = set()
        for log in logs:
            c = self.clean_log(log)
            # Deduplicate by message+timestamp
            key = (c.get("message"), c.get("timestamp"))
            if key not in seen:
                cleaned.append(c)
                seen.add(key)
        self.logger.info(f"Preprocessing complete. {len(cleaned)} logs remain after deduplication.")
        return cleaned

if __name__ == "__main__":
    # Example usage
    logs = [
        {"message": "User john.doe@email.com logged in", "timestamp": 123456},
        {"message": "User john.doe@email.com logged in", "timestamp": 123456},
        {"message": "Payment with card 4111 1111 1111 1111", "timestamp": 123457}
    ]
    pre = LogPreprocessor()
    cleaned = pre.preprocess_logs(logs)
    for log in cleaned:
        print(log)
