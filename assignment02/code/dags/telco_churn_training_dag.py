"""Airflow DAG: retraining, evaluation and challenger registration of the churn model.

ingest -> validate -> preprocess -> features -> train -> evaluate -> register

Triggered monthly (1st of the month, 02:00) **or** as soon as the drift monitor
publishes the ``DRIFT_ALERT`` dataset. The DAG stops at ``@challenger``;
promotion to ``@champion`` is a human decision (``src.pipeline promote``).
"""

from __future__ import annotations

import json
import logging
from datetime import timedelta
from typing import Any

import pendulum
from airflow import DAG
from airflow.timetables.datasets import DatasetOrTimeSchedule
from airflow.timetables.trigger import CronTriggerTimetable
from churnguard_common import (
    DEFAULT_ARGS,
    DRIFT_ALERT,
    TIMEZONE,
    post_alert,
    read_report,
    stage_task,
)

logger = logging.getLogger(__name__)


def notify_success(context: dict[str, Any]) -> None:
    """DAG success callback: announce the new challenger awaiting approval.

    Args:
        context: Airflow DAG-run context.
    """
    summary = read_report("challenger.json")
    payload = {
        "event": "challenger_registered",
        "run_id": context["run_id"],
        "model_uri": summary.get("model_uri"),
        "version": summary.get("version"),
        "run_name": summary.get("run_name"),
        "champion_version": summary.get("champion_version"),
        "next_step": "review and run `python -m src.pipeline promote --approved-by <name>`",
    }
    logger.info("SUCCESS %s", json.dumps(payload))
    post_alert(payload)


with DAG(
    dag_id="telco_churn_training",
    description="Monthly or drift-triggered retraining; registers a @challenger",
    default_args=DEFAULT_ARGS,
    schedule=DatasetOrTimeSchedule(
        timetable=CronTriggerTimetable("0 2 1 * *", timezone=TIMEZONE),
        datasets=[DRIFT_ALERT],
    ),
    start_date=pendulum.datetime(2026, 9, 1, tz=TIMEZONE),
    catchup=False,
    max_active_runs=1,
    dagrun_timeout=timedelta(hours=2),
    on_success_callback=notify_success,
    params={"experiments": []},
    tags=["ddm501", "churn", "training"],
    doc_md=__doc__,
) as dag:
    ingest = stage_task("ingest", retries=3)  # network download: retry transient errors
    validate = stage_task("validate", retries=0)  # bad data is deterministic: fail fast
    preprocess = stage_task("preprocess")
    features = stage_task("features")
    train = stage_task(
        "train",
        extra_args=(
            "{% if params.experiments %}--only {{ params.experiments | join(' ') }}{% endif %}"
        ),
        execution_timeout=timedelta(minutes=60),
        retries=1,
    )
    evaluate = stage_task("evaluate")
    register = stage_task("register", retries=1)

    ingest >> validate >> preprocess >> features >> train >> evaluate >> register


if __name__ == "__main__":
    for task in dag.topological_sort():
        print(f"{task.task_id:<11} retries={task.retries} timeout={task.execution_timeout}")
