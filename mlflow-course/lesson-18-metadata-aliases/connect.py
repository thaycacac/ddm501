"""
BÀI 18 — shared connect: stack bài 16 + model đã register ở bài 17.
"""
from __future__ import annotations

import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from mlflow import MlflowClient

STACK_ENV = Path(__file__).resolve().parent.parent / "lesson-16-docker-mlflow-stack" / ".env"
load_dotenv(STACK_ENV)

TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5001")
MODEL_NAME = "course-17-classifier"


def client() -> MlflowClient:
    # Giống extend: MlflowClient(tracking_uri=...) — không cần set_experiment
    # vì registry không thuộc experiment nào.
    return MlflowClient(tracking_uri=TRACKING_URI)


def show_pg(sql: str, params: tuple = ()) -> None:
    """Chạy một câu SELECT trên Postgres của stack bài 16 và in từng dòng."""
    conn = psycopg2.connect(host="127.0.0.1", port=int(os.getenv("POSTGRES_PORT", "25432")),
                            user="mlflow", password="mlflow", dbname="mlflow")
    with conn, conn.cursor() as cur:
        cur.execute(sql, params)
        for row in cur.fetchall():
            print("   ", row)
    conn.close()
