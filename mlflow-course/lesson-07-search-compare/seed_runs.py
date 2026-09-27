"""
BÀI 07 — Ghi vài run khác nhau để có cái mà so sánh.

Chạy với MLFLOW_TRACKING_URI=http://127.0.0.1:5001 (server SQLite đang bật).
"""
from __future__ import annotations

import os

import mlflow
import numpy as np
from sklearn.datasets import load_breast_cancer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5001")
EXPERIMENT = "mlflow-course-07"

CONFIGS = [
    ("logreg", {"C": 0.1}),
    ("logreg", {"C": 1.0}),
    ("rf", {"n_estimators": 50, "max_depth": 3}),
    ("rf", {"n_estimators": 100, "max_depth": None}),
]


def build(family: str, params: dict):
    if family == "logreg":
        clf = LogisticRegression(max_iter=5000, random_state=0, **params)
    else:
        clf = RandomForestClassifier(random_state=0, **params)
    return make_pipeline(StandardScaler(), clf)


def main() -> None:
    mlflow.set_tracking_uri(TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT)

    X, y = load_breast_cancer(return_X_y=True)
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    for family, params in CONFIGS:
        name = f"{family}-" + "-".join(str(v) for v in params.values())
        model = build(family, params)
        with mlflow.start_run(run_name=name):
            scores = cross_val_score(model, X_tr, y_tr, cv=3, scoring="roc_auc")
            model.fit(X_tr, y_tr)
            auc = float(roc_auc_score(y_te, model.predict_proba(X_te)[:, 1]))

            mlflow.log_params({"family": family, **params})
            mlflow.log_metrics(
                {
                    "cv_roc_auc_mean": float(np.mean(scores)),
                    "cv_roc_auc_std": float(np.std(scores)),
                    "test_roc_auc": auc,
                }
            )
            print(f"logged {name:20s}  cv={np.mean(scores):.5f}  test={auc:.5f}")

    print(f"\n{len(CONFIGS)} runs → experiment '{EXPERIMENT}'")


if __name__ == "__main__":
    main()
