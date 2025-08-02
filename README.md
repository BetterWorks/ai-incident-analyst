# ai-debug-agent

AI Debug Agent is an end-to-end pipeline for automated log ingestion, preprocessing, embedding, vector search, root cause analysis (RCA), and fix suggestion using LLMs (Retrieval-Augmented Generation). It features a Flask dashboard, Slack integration, and robust integration tests.

## Table of Contents
- [Project Overview](#ai-debug-agent)
- [Setup Instructions](#setup-instructions-for-ai-debug-agent)
- [Environment Variables](#environment-variables)
- [Dashboard (Flask Web UI)](#3-dashboard-flask-web-ui)
- [Slack Integration](#7-slack-integration)
- [LLM Processor (Ollama/Llama 3, RAG)](#6-llm-processor-ollamallama-3-rag)
- [Integration Tests](#4-integration-tests)
- [Contributing](#contributing)
- [Code Style & Linting](#code-style--linting)
- [Notes](#notes)

## 7. Slack Integration

The agent can send notifications, RCA summaries, and fix suggestions to a Slack channel using an incoming webhook.

### Setup
- Create a Slack Incoming Webhook and add the URL to your `.env`:
  ```
  SLACK_WEBHOOK_URL=https://hooks.slack.com/services/your/webhook/url
  ```

### Usage
You can send a message using the SlackNotifier class:

```sh
python src/slack_integration/slack_notifier.py
```
Or use it in your pipeline to send LLM results to Slack.

### Example
```python
from slack_integration.slack_notifier import SlackNotifier
notifier = SlackNotifier()
notifier.send_message("Test message from ai-debug-agent!")
```

# Setup Instructions for ai-debug-agent

## 1. Python Virtual Environment (Recommended)

To avoid dependency conflicts, use a virtual environment:

```sh
python -m venv venv
source venv/bin/activate
```

## 2. Install Dependencies

```sh
pip install -r requirements.txt
```

## 3. Dashboard (Flask Web UI)

The dashboard provides a web UI for RCA/fix history, search, feedback, metrics, and Slack sharing.

- Start the dashboard:
  ```sh
  python src/dashboard/app.py
  ```
- Visit [http://localhost:5000](http://localhost:5000) in your browser.
- Features:
  - RCA/fix history table with search/filter
  - RCA detail view with feedback (thumbs up/down, comments)
  - Export as PDF (print-friendly)
  - Share to Slack
  - Metrics page: incident timeline, by service, by severity (Chart.js)

### Requirements
- Flask (see requirements.txt)
- Chart.js and Bootstrap (CDN, no install needed)

## 4. Integration Tests

Run integration tests with:
```sh
pytest integration_tests/
```


## Environment Variables

Create a `.env` file in the project root. See `.env.example` for all available variables. Key variables include:

```
# New Relic
NEW_RELIC_API_KEY=your_new_relic_api_key_here
NEW_RELIC_ACCOUNT_ID=your_account_id_here
NR_LOG_SOURCE_TABLE=Log
NR_NAMESPACE_NAME=your_namespace
NR_CONTAINER_NAME=%conversations%
NR_MESSAGE_HEALTH_FILTER=%/health%
NR_MESSAGE_HTTP_FILTER=%HTTP/1.1%
NR_TIME_WINDOW=24 hours ago
NR_LIMIT_COUNT=1000
NEW_RELIC_NRQL_QUERY=

# Embedding
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_BATCH_SIZE=32
EMBEDDING_FIELDS=message,event

# Vector DB
FAISS_DB_PATH=faiss_index.bin

# LLM
OLLAMA_URL=http://localhost:11434/api/generate
LLM_MODEL=llama3
RAG_TOP_K=5
SLACK_NOTIFY=false

# Slack
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/your/webhook/url

# Dashboard
DASHBOARD_HISTORY_PATH=rca_history.json
DASHBOARD_SECRET_KEY=change-this-to-a-very-secret-key
```

> **Note:** Never commit your real `.env` file. Use `.env.example` for sharing config structure.
## Contributing

Contributions are welcome! Please open issues or pull requests for improvements, bug fixes, or new features.

## Code Style & Linting

This project recommends [black](https://github.com/psf/black) for formatting and [flake8](https://github.com/PyCQA/flake8) for linting. To check code style:

```sh
black --check .
flake8
```

To auto-format:
```sh
black .
```

## .gitignore

Ensure your `.gitignore` includes:
```
.env
__pycache__/
.pytest_cache/
.venv/
faiss_index.bin*
*.pyc
rca_history.json
```


## 4. Load Environment Variables

Before running any scripts, load the environment variables:

```sh
export $(grep -v '^#' .env | xargs)
```


## 5. Run the Log Fetcher

```sh
python src/ingestion/new_relic_fetcher.py
```

## 6. LLM Processor (Ollama/Llama 3, RAG)

The LLM processor module uses Ollama (Llama 3) to generate root cause analysis (RCA) and fix suggestions for batches of logs, using Retrieval-Augmented Generation (RAG) with context from the FAISS vector DB.

### Improvements
- Aggregates RAG context from all logs in the batch (not just the first).
- Retries Ollama API calls up to 3 times for robustness.
- Logs LLM prompts and responses with sensitive data redacted.

### Requirements
- Ollama running locally with the Llama 3 model pulled:
  ```sh
  ollama pull llama3
  ollama serve
  ```
  (By default, the agent expects Ollama at `http://localhost:11434`.)
- All prior modules (ingestion, preprocessing, embedding, vector DB) must be working and configured.

### Usage
You can use the LLM processor in your pipeline, or run the integration test:

```sh
python integration_tests/test_embedding_to_llm.py
```
This test runs the full pipeline: preprocessing → embedding → vector DB → LLM (RAG).

### Configuration
- LLM and RAG settings are controlled via `.env`:
  - `OLLAMA_URL` (default: http://localhost:11434/api/generate)
  - `LLM_MODEL` (default: llama3)
  - `RAG_TOP_K` (default: 5)

### Output
The LLM processor returns a summary and fix suggestion for the input logs, using similar logs from the vector DB as context.

## Notes
- Always activate your virtual environment before running scripts.
- Use `python` (not `python3`) for all commands.
- If you encounter environment variable errors, ensure you have exported them as shown above.
- For persistent environments, consider adding the export command to your shell profile or using a tool like `python-dotenv`.
