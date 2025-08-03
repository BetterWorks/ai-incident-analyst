

from src.config import get_config
import requests
from logging_utils.logger import setup_logger


class NewRelicLogFetcher:
    def validate_log_source_table(self):
        """Check if the log source table is valid by running a simple NRQL query."""
        test_query = f"SELECT count(*) FROM {self.log_source_table} SINCE 1 day ago LIMIT 1"
        graphql_query = f"""
        {{
          actor {{
            account(id: {self.account_id}) {{
              nrql(query: \"{test_query}\") {{
                results
              }}
            }}
          }}
        }}
        """
        headers = {
            "API-Key": self.api_key,
            "Content-Type": "application/json"
        }
        payload = {"query": graphql_query}
        try:
            response = requests.post(self.url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            if data.get("data", {}).get("actor", {}).get("account", {}).get("nrql", {}).get("results") is not None:
                return True
            else:
                self.logger.error(f"Log source table '{self.log_source_table}' is invalid or inaccessible. API response: {data}")
                return False
        except Exception as e:
            self.logger.error(f"Error validating log source table '{self.log_source_table}': {e}")
            return False
    def __init__(self):
        """
        All configuration is loaded from the .env file. To change log filtering, edit the .env file:
        - NEW_RELIC_API_KEY
        - NEW_RELIC_ACCOUNT_ID
        - NR_LOG_SOURCE_TABLE (e.g. Log, Log_dev1)
        - NR_NAMESPACE_NAME
        - NR_CONTAINER_NAME
        - NR_MESSAGE_HEALTH_FILTER
        - NR_MESSAGE_HTTP_FILTER
        - NR_MESSAGE_ERROR_FILTER
        - NR_TIME_WINDOW
        - NR_LIMIT_COUNT
        - NEW_RELIC_NRQL_QUERY (optional: full custom query)
        """
        self.api_key = get_config("NEW_RELIC_API_KEY", required=True)
        self.account_id = get_config("NEW_RELIC_ACCOUNT_ID", required=True)
        self.url = "https://api.newrelic.com/graphql"
        self.logger = setup_logger()
        self.logger.info("Successfully loaded New Relic API key and Account ID from config.")
        # Configurable query parts from config
        self.log_source_table = get_config("NR_LOG_SOURCE_TABLE", default="Log, Log_dev1")
        self.namespace_name = get_config("NR_NAMESPACE_NAME", default="betterworks-rainforest")
        self.container_name = get_config("NR_CONTAINER_NAME", default="%conversations%")
        self.message_health_filter = get_config("NR_MESSAGE_HEALTH_FILTER", default="%/health%")
        self.message_error_filter = get_config("NR_MESSAGE_ERROR_FILTER", default="%error%")
        self.message_http_filter = get_config("NR_MESSAGE_HTTP_FILTER", default="%HTTP/1.1%")
        self.time_window = get_config("NR_TIME_WINDOW", default="24 hours ago")
        self.limit_count = get_config("NR_LIMIT_COUNT", default="1000")
        # Compose NRQL query: allow full override, else build from config
        self.nrql_query = get_config("NEW_RELIC_NRQL_QUERY")
        if not self.nrql_query:
            self.nrql_query = (
                f"SELECT `level`,`container_name`,`message`,`event`,`namespace_name` FROM {self.log_source_table} "
                f"WHERE `namespace_name` = '{self.namespace_name}' "
                f"AND `message` NOT LIKE '{self.message_health_filter}' "
                f"AND `message` NOT LIKE '{self.message_http_filter}' "
                f"AND `container_name` LIKE '{self.container_name}' "
                f"AND `message` LIKE '{self.message_error_filter}' "
                f"SINCE {self.time_window} LIMIT {self.limit_count}"
            )

    def fetch_logs(self, nrql_query=None, debug=False):
        query = nrql_query or self.nrql_query
        graphql_query = f"""
        {{
          actor {{
            account(id: {self.account_id}) {{
              nrql(query: \"{query}\") {{
                results
              }}
            }}
          }}
        }}
        """
        headers = {
            "API-Key": self.api_key,
            "Content-Type": "application/json"
        }
        payload = {"query": graphql_query}
        response = requests.post(self.url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        # Robust error handling for missing/malformed responses
        try:
            logs = data["data"]["actor"]["account"]["nrql"]["results"]
        except Exception as e:
            self.logger.error(f"Malformed or missing response from New Relic API: {e}")
            self.logger.error(f"Full API response: {data}")
            return []
        self.logger.info(f"Fetched {len(logs)} logs from New Relic.")
        if debug:
            self.logger.info(f"Raw API response: {data}")
        return logs

if __name__ == "__main__":
    fetcher = NewRelicLogFetcher()
    logs = fetcher.fetch_logs(debug=True)
    for log in logs:
        print(log)
