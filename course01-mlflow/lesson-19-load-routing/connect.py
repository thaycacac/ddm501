"""
BÀI 19 — shared connect: stack bài 16 + model/alias từ bài 17–18.

.env bài 16 có cả 3 biến S3 → load_model tự tải file model từ MinIO.
"""
from __future__ import annotations

import os
from pathlib import Path

import mlflow
from dotenv import load_dotenv

STACK_ENV = Path(__file__).resolve().parent.parent / "lesson-16-docker-mlflow-stack" / ".env"
load_dotenv(STACK_ENV)

TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5001")
MODEL_NAME = "course-17-classifier"


def connect() -> None:
    # Chỉ load model, không log run → không cần set_experiment
    mlflow.set_tracking_uri(TRACKING_URI)
    print(f"tracking_uri = {mlflow.get_tracking_uri()}")
