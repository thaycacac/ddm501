"""
BÀI 15 — Bước 3: chế độ ② PROXY (cách của tutorial03).

Server bật với:  --artifacts-destination s3://mlflow/proxied   (+ biến S3 cho SERVER)
→ artifact_uri của run là mlflow-artifacts:/... → script gửi file qua HTTP cho
  server; SERVER gọi boto3 upload lên MinIO.

Script này KHÔNG gọi use_s3_env(): client không biết MinIO ở đâu, không có key.

  python step3_log_proxy.py
"""
from __future__ import annotations

import os
from pathlib import Path

import mlflow

from connect import EXPERIMENT_PROXY, S3_ENV, connect, minio_keys_of_run

TMP = Path(__file__).resolve().parent / "_tmp"
TMP.mkdir(exist_ok=True)


def main() -> None:
    # Chắc chắn client sạch biến S3, kể cả khi terminal lỡ export trước đó
    for key in S3_ENV:
        os.environ.pop(key, None)
    connect(EXPERIMENT_PROXY)
    print()

    with mlflow.start_run(run_name="proxy") as run:
        mlflow.log_param("mode", "proxy")
        mlflow.log_metric("answer", 42.0)
        print(f"run_id       = {run.info.run_id}")
        print(f"artifact_uri = {run.info.artifact_uri}")

        note = TMP / "notes.txt"
        note.write_text(f"run_id={run.info.run_id}\n", encoding="utf-8")
        # artifact_uri bắt đầu bằng mlflow-artifacts:/ → MLflow chọn
        # HttpArtifactRepository → HTTP PUT tới /api/2.0/mlflow-artifacts/... của server
        mlflow.log_artifact(str(note))

    print(f"\nstatus                = {mlflow.get_run(run.info.run_id).info.status}")
    # Soi MinIO bằng key của BÀI HỌC — client của bạn ở trên không hề dùng key này
    print(f"file trong MinIO      = {minio_keys_of_run(run.info.run_id)}")


if __name__ == "__main__":
    main()
