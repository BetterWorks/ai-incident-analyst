# AI Incident Analyst

AI Incident Analyst is an end-to-end pipeline for automated log ingestion, preprocessing, embedding, vector search, root cause analysis (RCA), and fix suggestion using LLMs (Retrieval-Augmented Generation). It features a Flask dashboard, Slack integration, and robust integration tests.

## Project Structure

```
ai-incident-analyst/
├── main.py                           # Main pipeline entry point
├── requirements.txt                  # Python dependencies
├── pyproject.toml                   # Project configuration (linting, formatting)
├── .env.example                     # Environment variables template
├── README.md                        # This file
├── integration_tests/               # End-to-end integration tests
│   ├── test_embedding_to_llm.py
│   ├── test_embedding_to_vector_db.py
│   ├── test_ingestion_to_preprocessing.py
│   ├── test_llm_to_slack.py
│   ├── test_new_relic_to_llm.py
│   └── test_preprocessing_to_embedding.py
└── src/                            # Source code modules
    ├── config.py                   # Configuration management
    ├── dashboard/                  # Flask web dashboard
    │   ├── app.py
    │   └── templates/
    ├── embedding/                  # Log embedding with sentence transformers
    │   └── embedder.py
    ├── ingestion/                  # New Relic log fetching
    │   ├── new_relic_fetcher.py
    │   └── logging_utils/
    ├── llm/                        # LLM processing with Ollama/RAG
    │   └── llm_processor.py
    ├── preprocessing/              # Log cleaning and preparation
    │   └── preprocessor.py
    ├── slack_integration/          # Slack notifications
    │   └── slack_notifier.py
    └── vector_db/                  # FAISS vector database
        └── faiss_db.py
```

## Table of Contents
- [Project Overview](#ai-incident-analyst)
- [Setup Instructions](#setup-instructions)
- [Environment Variables](#environment-variables)
- [Usage](#usage)
- [Dashboard (Flask Web UI)](#dashboard-flask-web-ui)
- [LLM Processor (Ollama/Llama 3, RAG)](#llm-processor-ollamallama-3-rag)
- [Slack Integration](#slack-integration)
- [Integration Tests](#integration-tests)
- [Contributing](#contributing)
- [Code Style & Linting](#code-style--linting)
- [Notes](#notes)

## Setup Instructions

### 1. Python Virtual Environment (Recommended)

To avoid dependency conflicts, use a virtual environment:

```sh
python -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

```sh
pip install -r requirements.txt
```

### 3. Environment Configuration

Create a `.env` file in the project root by copying the example file:

```sh
cp .env.example .env
```

Then edit the `.env` file and fill in your specific values. See the [Environment Variables](#environment-variables) section below for all available variables.

Before running any scripts, load the environment variables:

```sh
export $(grep -v '^#' .env | xargs)
```

## Usage

### Running the Complete Pipeline

To run the full AI Incident Analyst pipeline:

```sh
# Run with default settings (last 24 hours)
python main.py

# Run with specific time range
python main.py --from "2024-01-01 10:00:00" --to "2024-01-01 11:00:00"

# Run with custom batch size and Slack notifications
python main.py --batch-size 10 --slack

# Show help for all options
python main.py --help
```

### Individual Components

You can also run individual components:

#### 1. Log Ingestion
```sh
python src/ingestion/new_relic_fetcher.py
```

#### 2. Start the Dashboard
```sh
python src/dashboard/app.py
```

#### 3. Send Slack Notifications
```sh
python src/slack_integration/slack_notifier.py
```

## Dashboard (Flask Web UI)

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

## LLM Processor (Ollama/Llama 3, RAG)

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

## Slack Integration

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
notifier.send_message("Test message from AI Incident Analyst!")
```

## Integration Tests

Run integration tests with:
```sh
pytest integration_tests/
```


## Environment Variables

Create a `.env` file in the project root by copying from `.env.example`:

```sh
cp .env.example .env
```

Key variables include:

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
venv/
faiss_index.bin*
*.pyc
rca_history.json
```

## Notes
- Always activate your virtual environment before running scripts.
- Use `python` (not `python3`) for all commands.
- If you encounter environment variable errors, ensure you have exported them as shown above.
- For persistent environments, consider adding the export command to your shell profile or using a tool like `python-dotenv`.
