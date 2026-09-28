"""
BÀI 11c — Serve nhẹ (local HTTP) từ model đã register.

Cần MODEL_NAME@champion đã có (bài 10: lesson-10-classifier).
Agent sẽ hướng dẫn lệnh `mlflow models serve` trên chat — không chạy serve
bên trong script này (serve là process lâu dài).

File này chỉ: load pyfunc + predict 2 hàng để chứng minh model còn dùng được
trước khi bạn bật server.
"""
from __future__ import annotations

import os

import mlflow
import pandas as pd
from sklearn.datasets import load_breast_cancer
from sklearn.model_selection import train_test_split

TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5001")
MODEL_URI = os.getenv(
    "MODEL_URI", "models:/lesson-10-classifier@champion"
)


def main() -> None:
    mlflow.set_tracking_uri(TRACKING_URI)
    model = mlflow.pyfunc.load_model(MODEL_URI)
    X, y = load_breast_cancer(as_frame=True, return_X_y=True)
    _, X_te, _, _ = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )
    sample = X_te.head(2)
    pred = model.predict(sample)
    print(f"loaded {MODEL_URI}")
    print("sample predictions:", list(pred))
    print(
        "\nTiếp theo trên chat: mlflow models serve "
        f'-m "{MODEL_URI}" -p 5002 --env-manager local'
    )


if __name__ == "__main__":
    main()
