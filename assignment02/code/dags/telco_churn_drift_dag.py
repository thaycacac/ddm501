"""Airflow DAG: weekly input-drift monitor that can trigger retraining.

drift_check -> drift_detected (short-circuit) -> emit_drift_alert [outlet: DRIFT_ALERT]

Runs every Monday at 01:00, after the nightly extract and before the weekly
batch scoring. When any production feature has PSI > 0.2 against the training
reference, ``emit_drift_alert`` sends an alert and updates the ``DRIFT_ALERT``
dataset, which schedules ``telco_churn_training`` immediately. Otherwise the
alert task is skipped and nothing else happens.
"""

from __future__ import annotations

import json
import logging
from datetime import timedelta
from typing import Any

import pendulum
from airflow import DAG
from airflow.operators.python import PythonOperator, ShortCircuitOperator
from churnguard_common import (
    DEFAULT_ARGS,
    DRIFT_ALERT,
    TIMEZONE,
    post_alert,
    read_report,
    stage_task,
)

logger = logging.getLogger(__name__)


def drift_detected() -> bool:
    """Short-circuit condition: continue only if the latest drift report flags drift."""
    report = read_report("drift_report.json")
    logger.info("max PSI=%s drifted=%s", report.get("max_psi"), report.get("drifted_features"))
    return bool(report.get("drift_detected"))


def emit_drift_alert(**context: Any) -> dict[str, Any]:
    """Alert on-call and publish the drift event (the task's outlet triggers retraining).

    Args:
        **context: Airflow task context.

    Returns:
        Alert payload (stored as XCom).
    """
    report = read_report("drift_report.json")
    payload = {
        "event": "data_drift_detected",
        "run_id": context["run_id"],
        "max_psi": report.get("max_psi"),
        "drifted_features": report.get("drifted_features"),
        "action": "telco_churn_training scheduled via dataset " + DRIFT_ALERT.uri,
    }
    logger.warning("ALERT %s", json.dumps(payload))
    post_alert(payload)
    return payload


with DAG(
    dag_id="telco_churn_drift_monitor",
    description="Weekly PSI drift check; publishes DRIFT_ALERT to trigger retraining",
    default_args=DEFAULT_ARGS,
    schedule="0 1 * * 1",
    start_date=pendulum.datetime(2026, 9, 7, tz=TIMEZONE),
    catchup=False,
    max_active_runs=1,
    dagrun_timeout=timedelta(minutes=30),
    tags=["ddm501", "churn", "monitoring"],
    doc_md=__doc__,
) as dag:
    check = stage_task("drift", retries=2)
    gate = ShortCircuitOperator(task_id="drift_detected", python_callable=drift_detected)
    alert = PythonOperator(
        task_id="emit_drift_alert", python_callable=emit_drift_alert, outlets=[DRIFT_ALERT]
    )

    check >> gate >> alert
