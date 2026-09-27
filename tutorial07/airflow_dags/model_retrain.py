"""
Model retrain (manual or triggered by drift_monitoring).

train (scripts/training.py) -> quality gate -> promote to Production on MLflow
-> POST API /model/reload -> Telegram report with version and metrics.
The new version is always registered; only promotion is gated by min_accuracy.
"""

from typing import Any, Dict

import requests
from airflow import DAG
from airflow.decorators import task
from airflow.exceptions import AirflowFailException
from airflow.models.param import Param

from utils.common import API_URL, DEFAULT_ARGS, MLFLOW_PUBLIC_URL, RETRAIN_MIN_ACCURACY, START_DATE
from utils.telegram_alert import escape, send_telegram_message

RELOAD_TIMEOUT_SECONDS = 120


with DAG(
    dag_id="model_retrain",
    description="Retrain, register and promote the model on MLflow, reload the API, report to Telegram",
    schedule=None,
    start_date=START_DATE,
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    params={
        "min_accuracy": Param(RETRAIN_MIN_ACCURACY, type="number", minimum=0, maximum=1.5,
                              description="Promotion gate on test accuracy (set > 1 to force a failure)"),
        "reason": Param("manual", type="string", description="Why this retrain was requested"),
    },
    tags=["mlops", "training", "mlflow", "telegram"],
) as dag:

    @task
    def train_model(dag_run=None, params: Dict[str, Any] = None) -> Dict[str, Any]:
        # Imported at run time: keeps DAG parsing fast and independent of MLflow availability.
        from training import train_and_register

        reason = (dag_run.conf or {}).get("reason") if dag_run else None
        reason = reason or params["reason"]
        result = train_and_register(
            run_name=f"airflow_retrain_{dag_run.run_id}" if dag_run else "airflow_retrain",
            tags={"trigger": "airflow", "reason": reason, "airflow_run_id": dag_run.run_id if dag_run else "-"},
        )
        if not result["version"]:
            raise AirflowFailException("Model was logged but no registered version was found")
        result["reason"] = reason
        print(f"Registered {result['model_name']} v{result['version']} metrics={result['metrics']}")
        return result

    @task
    def quality_gate(result: Dict[str, Any], params: Dict[str, Any] = None) -> Dict[str, Any]:
        accuracy = result["metrics"]["accuracy"]
        min_accuracy = float(params["min_accuracy"])
        if accuracy < min_accuracy:
            # AirflowFailException skips retries: re-running will not change the metric.
            raise AirflowFailException(
                f"Quality gate failed: accuracy {accuracy:.4f} < min_accuracy {min_accuracy:.4f} "
                f"(version {result['version']} stays unpromoted)"
            )
        return result

    @task
    def promote_model(result: Dict[str, Any]) -> Dict[str, Any]:
        from training import promote_to_production

        promote_to_production(result["version"])
        print(f"Promoted {result['model_name']} v{result['version']} to Production")
        return result

    @task
    def reload_api(result: Dict[str, Any]) -> Dict[str, Any]:
        response = requests.post(f"{API_URL}/model/reload", timeout=RELOAD_TIMEOUT_SECONDS)
        response.raise_for_status()
        body = response.json()
        result["api_model_version"] = str(body.get("model_version"))
        print(f"API reload response: {body}")
        return result

    @task
    def notify_success(result: Dict[str, Any]) -> None:
        m = result["metrics"]
        send_telegram_message("\n".join([
            "<b>[RETRAIN] Model promoted to Production</b>",
            f"Model: <code>{escape(result['model_name'])}</code> v{escape(result['version'])} "
            f"(API serving v{escape(result.get('api_model_version', '?'))})",
            f"Accuracy: {m['accuracy']:.4f} | F1: {m['f1_score']:.4f}",
            f"Precision: {m['precision']:.4f} | Recall: {m['recall']:.4f}",
            f"Reason: {escape(result.get('reason', '-'))}",
            f"MLflow run: {escape(MLFLOW_PUBLIC_URL)}/#/experiments/{escape(result['experiment_id'])}"
            f"/runs/{escape(result['run_id'])}",
        ]))

    notify_success(reload_api(promote_model(quality_gate(train_model()))))
