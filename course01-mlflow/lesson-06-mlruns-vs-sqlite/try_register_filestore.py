"""
BÀI 06 — Log model trên file store (./mlruns) rồi thử register.

Chạy khi ĐÃ unset MLFLOW_TRACKING_URI và KHÔNG trỏ server.
Mục tiêu: cảm nhận giới hạn — registry cần backend DB.
"""
from __future__ import annotations

import mlflow
from sklearn.datasets import load_breast_cancer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

# CỐ Ý: không set_tracking_uri → file:./mlruns
mlflow.set_experiment("lesson-06-filestore")

X, y = load_breast_cancer(return_X_y=True)
X_tr, X_te, y_tr, y_te = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=0
)
model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=5000, random_state=0))
model.fit(X_tr, y_tr)

with mlflow.start_run(run_name="filestore-model") as run:
    mlflow.log_param("store", "filestore")
    mlflow.sklearn.log_model(model, artifact_path="model")
    run_id = run.info.run_id
    print(f"tracking_uri = {mlflow.get_tracking_uri()}")
    print(f"run_id       = {run_id}")
    print(f"model_uri    = runs:/{run_id}/model")

print("\nThử register (thường lỗi / không phù hợp với file store):")
try:
    mv = mlflow.register_model(f"runs:/{run_id}/model", "lesson-06-filestore-model")
    print(f"UNEXPECTED OK version={mv.version}")
except Exception as e:
    print(f"EXPECTED-ish failure: {type(e).__name__}: {e}")
