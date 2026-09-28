"""
BÀI 04 — hai dòng quyết định "run đi đâu".

mlflow.set_tracking_uri(...)  → WHERE  (server / folder nào lưu)
mlflow.set_experiment(...)    → WHICH  (experiment / "ngăn kéo" nào)

Quên dòng đầu → MLflow lặng lẽ ghi vào ./mlruns local;
UI bạn đang mở (server khác) sẽ KHÔNG thấy run.
Đây là lỗi phổ biến nhất khi mới học MLflow / Tutorial 02.
"""
from __future__ import annotations

import os

import mlflow

# Cùng convention với Tutorial 02 (_common.py). Port 5001 tránh AirPlay :5000 trên macOS.
TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5001")
EXPERIMENT = "mlflow-course-04"


def connect() -> None:
    mlflow.set_tracking_uri(TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT)
    print(f"tracking_uri = {mlflow.get_tracking_uri()}")
    print(f"experiment   = {EXPERIMENT}")
