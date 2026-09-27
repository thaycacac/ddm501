"""
BÀI 17 — Bước 1: tutorial02-extend/01_training.py, viết lại có comment.

2 run → 2 version của course-17-classifier:
  v1: RandomForest 100 cây, KHÔNG signature
  v2: RandomForest 500 cây, CÓ signature + input_example

Chạy lại script = thêm v3, v4... (registry chỉ thêm, không ghi đè — bài 09).
"""
from __future__ import annotations

import mlflow
import mlflow.sklearn
from mlflow.models import infer_signature
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

from connect import MODEL_NAME, connect
from data import get_data


def train_one(run_name: str, n_estimators: int, with_signature: bool) -> None:
    X_train, X_test, y_train, y_test = get_data()

    with mlflow.start_run(run_name=run_name) as run:
        # TAGS: nhãn để lọc/tìm (bài 05) → Postgres, bảng tags
        mlflow.set_tags({
            "owner": "dsteam",
            "algorithm": "random_forest",
            "dataset": "breast_cancer",
        })

        # PARAMS: cấu hình đầu vào → Postgres, bảng params.
        # Lấy từ CÙNG biến dùng để train, để param luôn khớp model thật.
        # (01_training.py run v2 ghi n_estimators=200 nhưng train 500 cây —
        #  param lệch model là lỗi hay gặp khi gõ số hai lần.)
        mlflow.log_params({"test_size": 0.2, "random_state": 42,
                           "n_estimators": n_estimators})

        model = RandomForestClassifier(n_estimators=n_estimators, random_state=42)
        model.fit(X_train, y_train)
        predictions = model.predict(X_test)
        acc = accuracy_score(y_test, predictions)
        mlflow.log_metric("accuracy", acc)  # → Postgres, bảng metrics

        extra = {}
        if with_signature:
            # infer_signature(input, output): nhìn dữ liệu thật để suy ra schema.
            # Input numpy → schema dạng tensor: float64, shape (-1, 30)
            extra["signature"] = infer_signature(X_test, predictions)
            # 5 hàng mẫu → file input_example.json cạnh model
            extra["input_example"] = X_test[:5]

        # log_model: đóng gói model (MLmodel, model.pkl, requirements...) rồi
        # upload lên artifact_uri của run → MinIO (s3://mlflow/artifacts/...).
        # registered_model_name: register luôn — tạo model nếu chưa có, rồi
        # thêm một version mới trỏ về runs:/<run_id>/model.
        info = mlflow.sklearn.log_model(
            sk_model=model,
            artifact_path="model",
            registered_model_name=MODEL_NAME,
            **extra,
        )

    print(f"\n{run_name}: accuracy={acc:.4f}  → {MODEL_NAME} "
          f"version {info.registered_model_version}  (run_id={run.info.run_id})")


def main() -> None:
    connect()
    train_one("breast_cancer_training_v1", n_estimators=100, with_signature=False)
    train_one("breast_cancer_training_v2", n_estimators=500, with_signature=True)
    print(f"\nUI → Models → {MODEL_NAME}")


if __name__ == "__main__":
    main()
