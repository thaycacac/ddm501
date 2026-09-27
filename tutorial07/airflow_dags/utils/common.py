"""Shared settings for the MLOps DAGs."""

import os
from datetime import datetime, timedelta

from utils.telegram_alert import task_failure_alert

API_URL = os.getenv("API_URL", "http://api:8000").rstrip("/")
MLFLOW_URL = os.getenv("MLFLOW_URL", "http://mlflow:5000").rstrip("/")
MLFLOW_PUBLIC_URL = os.getenv("MLFLOW_PUBLIC_URL", "http://localhost:5000").rstrip("/")
EVIDENTLY_URL = os.getenv("EVIDENTLY_URL", "http://evidently:8001").rstrip("/")
EVIDENTLY_PUBLIC_URL = os.getenv("EVIDENTLY_PUBLIC_URL", "http://localhost:8001").rstrip("/")

EVIDENTLY_DRIFT_THRESHOLD = float(os.getenv("EVIDENTLY_DRIFT_THRESHOLD", "0.1"))
DRIFT_WINDOW_SIZE = int(os.getenv("DRIFT_WINDOW_SIZE", "100"))
RETRAIN_MIN_ACCURACY = float(os.getenv("RETRAIN_MIN_ACCURACY", "0.8"))
HTTP_TIMEOUT_SECONDS = float(os.getenv("HTTP_TIMEOUT_SECONDS", "10"))

START_DATE = datetime(2025, 1, 1)

DEFAULT_ARGS = {
    "owner": "mlops",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=1),
    "on_failure_callback": task_failure_alert,
}
