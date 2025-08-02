import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.config import get_config
import requests
from logging_utils.logger import setup_logger

class SlackNotifier:
    def __init__(self, webhook_url=None):
        self.logger = setup_logger()
        self.webhook_url = webhook_url or get_config("SLACK_WEBHOOK_URL")
        if not self.webhook_url:
            raise ValueError("SLACK_WEBHOOK_URL must be set in environment or passed to SlackNotifier.")
        self.logger.info("SlackNotifier initialized.")

    def send_message(self, text, blocks=None):
        payload = {"text": text}
        if blocks:
            payload["blocks"] = blocks
        try:
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            self.logger.info("Slack message sent successfully.")
            return True
        except Exception as e:
            self.logger.error(f"Failed to send Slack message: {e}")
            return False

if __name__ == "__main__":
    # Example usage
    notifier = SlackNotifier()
    notifier.send_message("Test message from ai-debug-agent!")
