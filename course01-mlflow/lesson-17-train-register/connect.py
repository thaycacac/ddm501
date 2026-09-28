"""
BÀI 17 — shared connect: dùng stack bài 16 (Postgres + MinIO + MLflow trong Docker).

Đọc .env của bài 16 → có MLFLOW_TRACKING_URI + 3 biến S3 (chế độ DIRECT, bài 15):
script này tự upload model lên MinIO.
"""
from __future__ import annotations

import os
from pathlib import Path

import mlflow
from dotenv import load_dotenv

STACK_ENV = Path(__file__).resolve().parent.parent / "lesson-16-docker-mlflow-stack" / ".env"
load_dotenv(STACK_ENV)

TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5001")
EXPERIMENT = "mlflow-course-17"
MODEL_NAME = "course-17-classifier"


def connect() -> None:
    mlflow.set_tracking_uri(TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT)
    print(f"tracking_uri = {mlflow.get_tracking_uri()}")
    print(f"experiment   = {EXPERIMENT}")
