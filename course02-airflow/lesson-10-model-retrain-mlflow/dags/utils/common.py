"""BÀI 10 — Cấu hình chung (= tutorial07/airflow_dags/utils/common.py, phần model_retrain cần)."""
import os
from datetime import datetime, timedelta

from utils.telegram_alert import task_failure_alert

API_URL = os.getenv("API_URL", "http://api:8000").rstrip("/")
MLFLOW_PUBLIC_URL = os.getenv("MLFLOW_PUBLIC_URL", "http://localhost:5001").rstrip("/")
RETRAIN_MIN_ACCURACY = float(os.getenv("RETRAIN_MIN_ACCURACY", "0.8"))

START_DATE = datetime(2026, 9, 1)

DEFAULT_ARGS = {
    "owner": "mlops",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(seconds=20),
    "on_failure_callback": task_failure_alert,
}
