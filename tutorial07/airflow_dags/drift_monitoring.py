"""
Drift monitoring (hourly).

Calls Evidently POST /analyze, then branches on EVIDENTLY_DRIFT_THRESHOLD:
drift -> Telegram alert + trigger ``model_retrain``; otherwise finish quietly.
When Evidently has no reference/production data yet, the run is skipped (not failed).
"""

from typing import Any, Dict

import requests
from airflow import DAG
from airflow.decorators import task
from airflow.models.param import Param
from airflow.operators.empty import EmptyOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator

from utils.common import (
    DEFAULT_ARGS,
    DRIFT_WINDOW_SIZE,
    EVIDENTLY_DRIFT_THRESHOLD,
    EVIDENTLY_PUBLIC_URL,
    EVIDENTLY_URL,
    START_DATE,
)
from utils.telegram_alert import escape, send_telegram_message

ANALYZE_TIMEOUT_SECONDS = 120


with DAG(
    dag_id="drift_monitoring",
    description="Run Evidently drift analysis; alert Telegram and trigger model_retrain on drift",
    schedule="@hourly",
    start_date=START_DATE,
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    params={
        "threshold": Param(EVIDENTLY_DRIFT_THRESHOLD, type="number", minimum=0, maximum=1,
                           description="Share of drifted features above which drift is reported"),
        "window_size": Param(DRIFT_WINDOW_SIZE, type="integer", minimum=1,
                             description="Number of recent production samples to analyse"),
    },
    tags=["mlops", "drift", "evidently", "telegram"],
) as dag:

    @task
    def run_drift_analysis(params: Dict[str, Any] = None) -> Dict[str, Any]:
        threshold = float(params["threshold"])
        payload = {"window_size": int(params["window_size"]), "threshold": threshold}
        response = requests.post(f"{EVIDENTLY_URL}/analyze", json=payload, timeout=ANALYZE_TIMEOUT_SECONDS)

        if response.status_code == 400:
            detail = response.json().get("detail", response.text)
            print(f"Drift analysis skipped: {detail}")
            return {"status": "skipped", "detail": detail, "threshold": threshold}
        response.raise_for_status()

        result = response.json()
        total = result.get("total_features") or 0
        drifted = result.get("drifted_count") or 0
        # Evidently's drift_score is share_of_drifted_columns (only set when dataset drift is detected);
        # its per-column list can be empty depending on the Evidently version, so take the larger value.
        share = max(drifted / total if total else 0.0, float(result.get("drift_score") or 0.0))
        result["drifted_share"] = share
        result["threshold"] = threshold
        result["is_drift"] = bool(result.get("drift_detected")) or share > threshold
        print(f"drift_detected={result.get('drift_detected')} drifted={drifted}/{total} "
              f"share={share:.2f} threshold={threshold} -> is_drift={result['is_drift']}")
        return result

    @task.branch
    def decide(result: Dict[str, Any]) -> str:
        if result.get("status") == "skipped":
            return "no_drift"
        return "alert_drift" if result.get("is_drift") else "no_drift"

    @task
    def alert_drift(result: Dict[str, Any]) -> None:
        features = ", ".join(result.get("drifted_features") or []) or "-"
        send_telegram_message("\n".join([
            "<b>[DRIFT] Data drift detected</b>",
            f"Drifted features: {result.get('drifted_count')}/{result.get('total_features')} "
            f"(share {result['drifted_share']:.0%}, threshold {result['threshold']:.0%})",
            f"Features: <code>{escape(features)}</code>",
            f"Samples: reference={result.get('reference_samples')}, current={result.get('current_samples')}",
            f"Report: {escape(EVIDENTLY_PUBLIC_URL)}{escape(result.get('report_url', ''))}",
            "Action: triggering DAG <code>model_retrain</code>",
        ]))

    trigger_retrain = TriggerDagRunOperator(
        task_id="trigger_model_retrain",
        trigger_dag_id="model_retrain",
        conf={"reason": "drift_monitoring run {{ run_id }}"},
        wait_for_completion=False,
    )

    no_drift = EmptyOperator(task_id="no_drift")

    analysis = run_drift_analysis()
    branch = decide(analysis)
    branch >> no_drift
    branch >> alert_drift(analysis) >> trigger_retrain
