"""
BÀI 17 — Bước 2: đi từ tầng trên xuống tầng dưới của một model đã register.

  Registered model → Version → Run → Artifacts (file trong MinIO)

Với mỗi version in ra: run nào sinh ra nó, source nằm đâu, có signature không,
và trong thư mục model/ có những file gì.
"""
from __future__ import annotations

import mlflow
from mlflow import MlflowClient

from connect import MODEL_NAME, connect


def main() -> None:
    connect()
    client = MlflowClient()

    versions = sorted(client.search_model_versions(f"name = '{MODEL_NAME}'"),
                      key=lambda mv: int(mv.version))
    for mv in versions:
        run = client.get_run(mv.run_id)
        # get_model_info chỉ tải file MLmodel (nhỏ), không tải model.pkl
        info = mlflow.models.get_model_info(f"models:/{MODEL_NAME}/{mv.version}")
        files = [a.path for a in client.list_artifacts(mv.run_id, "model")]

        print(f"\n=== {MODEL_NAME} version {mv.version} ===")
        print(f"  run         = {run.info.run_name}  ({mv.run_id})")
        print(f"  params      = {run.data.params}")
        print(f"  accuracy    = {run.data.metrics.get('accuracy'):.4f}")
        # source: version trỏ về đâu (runs:/<run_id>/model hoặc s3://...).
        # Dù dạng nào, file thật nằm dưới artifact_uri của run → MinIO.
        print(f"  source      = {mv.source}")
        print(f"  artifact    = {run.info.artifact_uri}/model")
        print(f"  signature   = {info.signature}")
        print(f"  model files = {files}")


if __name__ == "__main__":
    main()
