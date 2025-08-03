
import os
import sys
import json
from flask import Flask, render_template, request, redirect, url_for, flash
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from slack_integration.slack_notifier import SlackNotifier
from logging_utils.logger import setup_logger
from src.config import get_config

app = Flask(__name__, template_folder="templates")
app.secret_key = get_config("DASHBOARD_SECRET_KEY", default="change-this-to-a-very-secret-key")
logger = setup_logger()

@app.route("/metrics")
def metrics():
    history = load_history()
    # Prepare data for charts
    from collections import Counter, defaultdict
    import datetime
    # Timeline: count by day
    timeline = defaultdict(int)
    for entry in history:
        ts = entry.get("timestamp", "")[:10]
        if ts:
            timeline[ts] += 1
    timeline_sorted = sorted(timeline.items())
    # By service
    service_counts = Counter(e.get("container_name", "unknown") for e in history)
    # By namespace
    namespace_counts = Counter(e.get("namespace_name", "unknown") for e in history)
    # By level
    level_counts = Counter(e.get("level", "unknown") for e in history)
    return render_template(
        "metrics.html",
        timeline_labels=[d for d, _ in timeline_sorted],
        timeline_values=[c for _, c in timeline_sorted],
        service_labels=list(service_counts.keys()),
        service_values=list(service_counts.values()),
        namespace_labels=list(namespace_counts.keys()),
        namespace_values=list(namespace_counts.values()),
        level_labels=list(level_counts.keys()),
        level_values=list(level_counts.values()),
    )

# For MVP, use a JSON file as persistent storage for RCA/fix history
def load_history():
    """Load RCA/fix history from persistent storage."""
    path = get_config("DASHBOARD_HISTORY_PATH", default="rca_history.json")
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                content = f.read().strip()
                if not content:
                    return []
                return json.loads(content)
        except Exception as e:
            logger.warning(f"Could not load dashboard history: {e}")
            return []
    return []

@app.route("/")
def home():
    history = load_history()
    # Get search params
    service = request.args.get("service", "").strip().lower()
    namespace = request.args.get("namespace", "").strip().lower()
    level = request.args.get("level", "").strip().lower()
    keyword = request.args.get("keyword", "").strip().lower()
    # Filter
    def match(entry):
        if service and service not in (entry.get("container_name", "").lower()):
            return False
        if namespace and namespace not in (entry.get("namespace_name", "").lower()):
            return False
        if level and level != (entry.get("level", "").lower()):
            return False
        if keyword:
            # Search in llm_output, logs, similar logs
            text = json.dumps(entry).lower()
            if keyword not in text:
                return False
        return True
    filtered = [e for e in history if match(e)]
    # Sort by most recent
    filtered = sorted(filtered, key=lambda x: x.get("timestamp", ""), reverse=True)
    return render_template("home.html", history=filtered, service=service, namespace=namespace, level=level, keyword=keyword)


# Utility function, not a route
def save_history(history):
    """Save RCA/fix history to persistent storage."""
    path = get_config("DASHBOARD_HISTORY_PATH", default="rca_history.json")
    with open(path, "w") as f:
        json.dump(history, f, indent=2)

@app.route("/rca/<int:idx>", methods=["GET", "POST"])
def rca_detail(idx):
    history = load_history()
    if not (0 <= idx < len(history)):
        return "Not found", 404
    entry = history[idx]
    feedback = entry.get("feedback", {})
    # Remove 'embedding' from logs for display
    def strip_embedding(logs):
        return [
            {k: v for k, v in log.items() if k != "embedding"}
            for log in logs
        ]
    entry_display = dict(entry)
    if "batch_logs" in entry_display:
        entry_display["batch_logs"] = strip_embedding(entry_display["batch_logs"])
    if "similar_logs" in entry_display:
        entry_display["similar_logs"] = strip_embedding(entry_display["similar_logs"])
    if request.method == "POST":
        # Save feedback
        feedback_type = request.form.get("feedback_type")
        comment = request.form.get("comment", "").strip()
        feedback = feedback or {}
        if feedback_type in ("up", "down"):
            feedback["vote"] = feedback_type
        if comment:
            feedback["comment"] = comment
        entry["feedback"] = feedback
        history[idx] = entry
        save_history(history)
        return redirect(url_for("rca_detail", idx=idx))
    return render_template("rca_detail.html", entry=entry_display, idx=idx, feedback=feedback)

# Share to Slack endpoint
@app.route("/rca/<int:idx>/share_slack", methods=["POST"])
def share_to_slack(idx):
    history = load_history()
    if not (0 <= idx < len(history)):
        return "Not found", 404
    entry = history[idx]
    # Format message
    msg = f"*AI RCA & Fix Suggestion:*\n*Logs:*\n"
    for log in entry.get("batch_logs", []):
        namespace = log.get('namespace_name', '')
        namespace_text = f" | {namespace}" if namespace else ""
        msg += f"- {log.get('timestamp', '')} | {log.get('container_name', '')} | {log.get('level', '')}{namespace_text} | {log.get('message', '')}\n"
    msg += f"\n*RCA & Fix:*\n{entry.get('llm_output', '')}"
    try:
        notifier = SlackNotifier()
        ok = notifier.send_message(msg)
        if ok:
            flash("Shared to Slack successfully!", "success")
        else:
            flash("Failed to send to Slack.", "danger")
    except Exception as e:
        flash(f"Slack error: {e}", "danger")
    return redirect(url_for("rca_detail", idx=idx))

if __name__ == "__main__":
    app.run(debug=True)
