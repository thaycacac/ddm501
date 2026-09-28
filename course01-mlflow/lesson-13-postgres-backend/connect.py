"""
BÀI 13 — shared connect (cùng convention bài 04–11: server :5001).

WHERE = tracking URI | WHICH = experiment name

Khác bài 04–11: server phía sau dùng Postgres thay vì SQLite. Script ML KHÔNG
cần biết điều đó — nó vẫn chỉ nói chuyện với http://127.0.0.1:5001.

PG chỉ dùng cho BÀI HỌC (mở nắp xem DB). Code ML thật không nối thẳng vào đây.
"""
from __future__ import annotations

import os

import mlflow

TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5001")
EXPERIMENT = "mlflow-course-13"

# 5 mảnh này ghép lại chính là --backend-store-uri của mlflow server:
#   postgresql://mlflow:mlflow@127.0.0.1:25432/mlflow
PG = {
    "host": "127.0.0.1",   # máy bạn → đi qua port đã publish
    "port": 25432,         # "25432:5432" trong docker-compose.yml
    "user": "mlflow",      # POSTGRES_USER
    "password": "mlflow",  # POSTGRES_PASSWORD
    "dbname": "mlflow",    # POSTGRES_DB
}


def connect() -> None:
    mlflow.set_tracking_uri(TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT)
    print(f"tracking_uri = {mlflow.get_tracking_uri()}")
    print(f"experiment   = {EXPERIMENT}")
