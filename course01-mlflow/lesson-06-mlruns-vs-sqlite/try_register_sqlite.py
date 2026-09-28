"""
BÀI 06 — Cùng ý tưởng nhưng trên server SQLite (MLFLOW_TRACKING_URI=http://127.0.0.1:5001).

Register phải thành công → Model Registry sống trong DB backend.
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
mlflow.set_tracking_uri(TRACKING_URI)
mlflow.set_experiment("lesson-06-sqlite")

X, y = load_breast_cancer(return_X_y=True)
X_tr, X_te, y_tr, y_te = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=0
)
model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=5000, random_state=0))
model.fit(X_tr, y_tr)

with mlflow.start_run(run_name="sqlite-model") as run:
    mlflow.log_param("store", "sqlite-server")
    mlflow.sklearn.log_model(model, artifact_path="model")
    run_id = run.info.run_id
    print(f"tracking_uri = {mlflow.get_tracking_uri()}")
    print(f"run_id       = {run_id}")

mv = mlflow.register_model(f"runs:/{run_id}/model", "lesson-06-sqlite-model")
print(f"registered OK  name={mv.name}  version={mv.version}")
print("UI → Models tab → lesson-06-sqlite-model")
