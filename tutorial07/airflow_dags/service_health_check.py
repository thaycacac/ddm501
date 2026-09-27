"""
Service health check (every 15 minutes).

Calls /health of the model API, MLflow and Evidently. When at least one service
is down, a single Telegram alert lists every failing service and the run is
marked failed (without triggering the generic failure callback a second time).
"""

from typing import Any, Dict, List

import requests
from airflow import DAG
from airflow.decorators import task
from airflow.exceptions import AirflowFailException

from utils.common import API_URL, DEFAULT_ARGS, EVIDENTLY_URL, HTTP_TIMEOUT_SECONDS, MLFLOW_URL, START_DATE
from utils.telegram_alert import escape, send_telegram_message

SERVICES = {
    "api": f"{API_URL}/health",
    "mlflow": f"{MLFLOW_URL}/health",
    "evidently": f"{EVIDENTLY_URL}/health",
}


with DAG(
    dag_id="service_health_check",
    description="Check /health of API, MLflow and Evidently; alert Telegram when a service is down",
    schedule="*/15 * * * *",
    start_date=START_DATE,
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["mlops", "monitoring", "telegram"],
) as dag:

    @task(retries=0)
    def check_service(name: str, url: str) -> Dict[str, Any]:
        """Never raises: a down service is reported as data, not as a task failure."""
        try:
            response = requests.get(url, timeout=HTTP_TIMEOUT_SECONDS)
        except requests.RequestException as exc:
            return {"service": name, "url": url, "healthy": False, "detail": f"{type(exc).__name__}: {exc}"[:300]}

        detail = f"HTTP {response.status_code}"
        healthy = response.status_code == 200
        try:
            body = response.json()
        except ValueError:
            body = None
        # API/Evidently return {"status": "healthy" | "unhealthy", ...}; MLflow returns plain "OK".
        if healthy and isinstance(body, dict) and "status" in body:
            healthy = body["status"] == "healthy"
            detail = f"HTTP {response.status_code}, status={body['status']}"
            if name == "api" and not body.get("model_loaded", True):
                detail += ", model_loaded=false"
        return {"service": name, "url": url, "healthy": healthy, "detail": detail}

    @task(retries=0, on_failure_callback=None)
    def report(results: List[Dict[str, Any]]) -> Dict[str, Any]:
        down = [r for r in results if not r["healthy"]]
        for r in results:
            print(f"{r['service']:<10} healthy={r['healthy']} ({r['detail']})")
        if not down:
            return {"healthy": True, "checked": len(results)}

        lines = [f"<b>[HEALTH CHECK] {len(down)}/{len(results)} service down</b>"]
        for r in down:
            lines.append(f"- <b>{escape(r['service'])}</b> ({escape(r['url'])}): {escape(r['detail'])}")
        send_telegram_message("\n".join(lines))
        raise AirflowFailException(f"Services down: {', '.join(r['service'] for r in down)}")

    checks = [check_service.override(task_id=f"check_{name}")(name, url) for name, url in SERVICES.items()]
    report(checks)
