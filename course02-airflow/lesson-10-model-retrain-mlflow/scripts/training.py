"""
BÀI 10 — Train / đăng ký / promote model trên MLflow. Bản của tutorial07/scripts/training.py.

DAG import file này LÚC CHẠY TASK (không phải lúc parse): /opt/airflow/scripts nằm trong PYTHONPATH.
Giữ nguyên hành vi tutorial07:
  - dataset sklearn load_wine (13 feature, 3 lớp), RandomForest, 4 metric
  - log_model(registered_model_name=...) → MỖI LẦN train sinh 1 version mới trong registry
  - promote = chuyển stage "Production" + archive bản Production cũ
Bổ sung: đặt thêm alias "champion" (cách mới của MLflow, course01 bài 18) và hàm đọc bản Production hiện tại.
"""
import os
from typing import Any, Dict, Optional

import mlflow
import mlflow.sklearn
from mlflow.tracking import MlflowClient
from sklearn.datasets import load_wine
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split

# Mọi endpoint đọc từ env (compose đặt). Trong container: mlflow:5000, minio:9000 (tên service trong
# mạng mlflow-course-16-net), KHÔNG phải 127.0.0.1:5001 như khi chạy trên máy.
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
MODEL_NAME = os.getenv("MODEL_NAME", "wine_quality_model")
EXPERIMENT_NAME = os.getenv("EXPERIMENT_NAME", "airflow-course-10")
PRODUCTION_ALIAS = "champion"

DEFAULT_PARAMS = {"n_estimators": 100, "max_depth": 10, "min_samples_split": 2, "random_state": 42}


def _client() -> MlflowClient:
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    return MlflowClient()


def train_and_register(run_name: str, params: Optional[dict] = None, tags: Optional[dict] = None) -> Dict[str, Any]:
    params = {**DEFAULT_PARAMS, **(params or {})}
    _client()
    mlflow.set_experiment(EXPERIMENT_NAME)

    X, y = load_wine(return_X_y=True)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    with mlflow.start_run(run_name=run_name) as run:
        if tags:
            mlflow.set_tags(tags)
        model = RandomForestClassifier(**params).fit(X_train, y_train)
        y_pred = model.predict(X_test)
        metrics = {
            "accuracy": accuracy_score(y_test, y_pred),
            "f1_score": f1_score(y_test, y_pred, average="weighted"),
            "precision": precision_score(y_test, y_pred, average="weighted"),
            "recall": recall_score(y_test, y_pred, average="weighted"),
        }
        mlflow.log_params(params)
        mlflow.log_metrics(metrics)
        # Artifact (model.pkl, MLmodel...) được CLIENT (task Airflow) upload thẳng lên MinIO
        # (chế độ direct của course01 bài 16) → container Airflow cần MLFLOW_S3_ENDPOINT_URL + key.
        mlflow.sklearn.log_model(
            model,
            artifact_path="model",
            registered_model_name=MODEL_NAME,     # đăng ký luôn → version mới
            signature=mlflow.models.infer_signature(X_train, y_pred),
            input_example=X_train[:2],
        )
        run_id, experiment_id = run.info.run_id, run.info.experiment_id

    # log_model không trả số version → tra registry theo run_id
    versions = _client().search_model_versions(f"name='{MODEL_NAME}' and run_id='{run_id}'")
    version = max(int(v.version) for v in versions) if versions else None
    return {
        "run_id": run_id,
        "experiment_id": experiment_id,
        "model_name": MODEL_NAME,
        "version": str(version) if version is not None else None,
        "metrics": metrics,
        "params": params,
    }


def get_production() -> Optional[Dict[str, Any]]:
    """Bản đang Production (version + accuracy của run sinh ra nó), None nếu chưa có."""
    client = _client()
    try:
        latest = client.get_latest_versions(MODEL_NAME, stages=["Production"])
    except mlflow.exceptions.MlflowException:
        return None            # registered model chưa tồn tại (lần train đầu tiên)
    if not latest:
        return None
    mv = latest[0]
    accuracy = client.get_run(mv.run_id).data.metrics.get("accuracy")
    return {"version": mv.version, "accuracy": accuracy}


def promote_to_production(version: str) -> None:
    client = _client()
    # Cách tutorial07 (stage): API load "models:/wine_quality_model/Production".
    # MLflow 2.9+ đánh dấu stage là deprecated (log có cảnh báo) nhưng vẫn chạy.
    client.transition_model_version_stage(
        name=MODEL_NAME, version=version, stage="Production",
        archive_existing_versions=True,   # bản Production cũ → Archived, luôn chỉ 1 bản Production
    )
    # Cách mới (alias): "models:/wine_quality_model@champion". Alias chỉ trỏ vào 1 version,
    # đặt lại là tự dời khỏi version cũ.
    client.set_registered_model_alias(MODEL_NAME, PRODUCTION_ALIAS, version)
