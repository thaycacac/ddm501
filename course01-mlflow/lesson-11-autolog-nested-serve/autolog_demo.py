"""
BÀI 11a — Autolog: MLflow tự log params/metrics/model khi fit().

Khi nào dùng:
  - Prototype nhanh, ít đụng tay log_*
Khi nào cẩn thận / không dùng một mình:
  - Cần metric/custom artifact riêng (recall malignant, confusion matrix…)
  - Cần kiểm soát chặt tên param — Tutorial 02 log tay vì vậy

Bật: mlflow.sklearn.autolog()
Tắt: mlflow.sklearn.autolog(disable=True)
"""
from __future__ import annotations

import os

import mlflow
from sklearn.datasets import load_breast_cancer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5001")
EXPERIMENT = "mlflow-course-11"


def main() -> None:
    mlflow.set_tracking_uri(TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT)

    mlflow.sklearn.autolog()  # tự log quanh fit()

    X, y = load_breast_cancer(return_X_y=True)
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=0
    )
    model = make_pipeline(
        StandardScaler(),
        LogisticRegression(C=1.0, max_iter=5000, random_state=0),
    )

    with mlflow.start_run(run_name="autolog-sklearn") as run:
        model.fit(X_tr, y_tr)
        # Không cần log_param/log_model tay — autolog đã làm quanh fit
        print(f"run_id = {run.info.run_id}")
        print("UI → mlflow-course-11 → autolog-sklearn → xem params/metrics/model tự có")

    mlflow.sklearn.autolog(disable=True)


if __name__ == "__main__":
    main()
