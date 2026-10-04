"""Shared Airflow building blocks for the ChurnGuard DAGs.

Holds the project paths, the drift-alert dataset that links the monitoring DAG to
the training DAG, the alerting callbacks and the factory for pipeline-stage tasks.
Tasks shell out to ``python -m src.pipeline <command>`` with the project's own
interpreter (``TELCO_PYTHON``), so Airflow only orchestrates and the ML
dependencies live in a separate environment/image.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
from datetime import timedelta
from pathlib import Path
from typing import Any

from airflow.datasets import Dataset
from airflow.operators.bash import BashOperator

logger = logging.getLogger(__name__)

PROJECT_DIR = Path(os.environ.get("TELCO_PROJECT_DIR", Path(__file__).resolve().parents[1]))
_venv_python = PROJECT_DIR / ".venv" / "bin" / "python"
PYTHON_BIN = os.environ.get(
    "TELCO_PYTHON", str(_venv_python) if _venv_python.exists() else "python"
)
REPORTS_DIR = PROJECT_DIR / "reports"
ALERT_WEBHOOK_URL = os.environ.get("ALERT_WEBHOOK_URL", "")
TIMEZONE = "Asia/Ho_Chi_Minh"

# Updated by the drift monitor when PSI exceeds the threshold; triggers retraining.
DRIFT_ALERT = Dataset("churnguard://monitoring/drift-alert")


def post_alert(payload: dict[str, Any]) -> None:
    """Send an alert to a Slack-compatible webhook; never raise from a callback."""
    if not ALERT_WEBHOOK_URL.startswith("https://"):
        return
    request = urllib.request.Request(  # noqa: S310 - scheme restricted to https above
        ALERT_WEBHOOK_URL,
        data=json.dumps({"text": json.dumps(payload)}).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(request, timeout=5)  # noqa: S310 - scheme restricted to https
    except OSError:
        logger.exception("Alert webhook delivery failed")


def notify_failure(context: dict[str, Any]) -> None:
    """Task failure callback: structured log line + optional webhook alert.

    Args:
        context: Airflow task context.
    """
    ti = context["task_instance"]
    payload = {
        "event": "task_failed",
        "dag_id": ti.dag_id,
        "task_id": ti.task_id,
        "run_id": context["run_id"],
        "try_number": ti.try_number,
        "exception": str(context.get("exception")),
        "log_url": ti.log_url,
    }
    logger.error("ALERT %s", json.dumps(payload))
    post_alert(payload)


def notify_retry(context: dict[str, Any]) -> None:
    """Task retry callback: warning-level structured log (no paging).

    Args:
        context: Airflow task context.
    """
    ti = context["task_instance"]
    logger.warning(
        "RETRY %s",
        json.dumps({"dag_id": ti.dag_id, "task_id": ti.task_id, "try_number": ti.try_number}),
    )


def read_report(name: str) -> dict[str, Any]:
    """Load a JSON report written by the pipeline (empty dict if missing)."""
    path = REPORTS_DIR / name
    return json.loads(path.read_text()) if path.exists() else {}


DEFAULT_ARGS: dict[str, Any] = {
    "owner": "retention-ml",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=30),
    "execution_timeout": timedelta(minutes=10),
    "on_failure_callback": notify_failure,
    "on_retry_callback": notify_retry,
}


def stage_task(command: str, extra_args: str = "", **overrides: Any) -> BashOperator:
    """Create a BashOperator running one ``src.pipeline`` command.

    Must be called inside a ``with DAG(...)`` block.

    Args:
        command: Pipeline stage or operation name (also used as ``task_id``).
        extra_args: Additional CLI arguments (Jinja-templated).
        **overrides: Operator keyword overrides (retries, timeout, ...).

    Returns:
        Configured operator.
    """
    return BashOperator(
        task_id=command,
        bash_command=f'cd "{PROJECT_DIR}" && "{PYTHON_BIN}" -m src.pipeline {command} {extra_args}',
        env={
            "TELCO_PROJECT_ROOT": str(PROJECT_DIR),
            "TELCO_PIPELINE_RUN_ID": "{{ run_id }}",
            "MLFLOW_DISABLE_AGENT_HINT": "1",
        },
        append_env=True,
        **overrides,
    )
