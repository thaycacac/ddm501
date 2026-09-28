"""
BÀI 11b — Nested runs: run cha + run con (vd: outer trial, inner fold).

Parent giữ tổng kết; children giữ chi tiết từng bước.
UI: mở parent → thấy nested runs.
"""
from __future__ import annotations

import os

import mlflow
import numpy as np
from sklearn.datasets import load_breast_cancer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5001")
EXPERIMENT = "mlflow-course-11"


def main() -> None:
    mlflow.set_tracking_uri(TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT)

    X, y = load_breast_cancer(return_X_y=True)
    cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=0)
    model = make_pipeline(
        StandardScaler(),
        LogisticRegression(C=1.0, max_iter=5000, random_state=0),
    )

    with mlflow.start_run(run_name="parent-cv") as parent:
        fold_means = []
        for i, (tr, te) in enumerate(cv.split(X, y), start=1):
            # nested=True → run con gắn vào parent
            with mlflow.start_run(run_name=f"fold-{i}", nested=True):
                scores = cross_val_score(
                    model, X[tr], y[tr], cv=2, scoring="roc_auc"
                )
                m = float(np.mean(scores))
                mlflow.log_metric("fold_proxy_auc", m)
                fold_means.append(m)
                print(f"  fold-{i} metric={m:.5f}")

        mlflow.log_metric("mean_fold_proxy_auc", float(np.mean(fold_means)))
        print(f"parent run_id = {parent.info.run_id}")
        print("UI → mở parent-cv → thấy các fold-* nested")


if __name__ == "__main__":
    main()
