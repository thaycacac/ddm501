"""
BÀI 05 — shared connect (cùng server :5001 với bài 04 nếu bạn để server chạy).

WHERE = tracking URI | WHICH = experiment name
"""
from __future__ import annotations

import os

import mlflow

TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5001")
EXPERIMENT = "mlflow-course-05"


def connect() -> None:
    mlflow.set_tracking_uri(TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT)
    print(f"tracking_uri = {mlflow.get_tracking_uri()}")
    print(f"experiment   = {EXPERIMENT}")
