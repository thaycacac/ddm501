"""
BÀI 16 — log 1 run từ MÁY BẠN vào stack chạy hoàn toàn trong Docker.

Giống bài 15 bước 2 (chế độ DIRECT), nhưng:
  - không còn cờ --with-s3-env: biến S3 đến từ .env qua load_dotenv
  - MLflow server giờ là container — script KHÔNG biết và KHÔNG cần biết

Đây chính là cách 01_training.py của tutorial02-extend chạy.
"""
from __future__ import annotations

import os
from pathlib import Path

import boto3
import mlflow

from connect import BUCKET, connect

TMP = Path(__file__).resolve().parent / "_tmp"
TMP.mkdir(exist_ok=True)


def keys_in_minio(run_id: str) -> list[str]:
    s3 = boto3.client("s3", endpoint_url=os.environ["MLFLOW_S3_ENDPOINT_URL"])
    keys = []
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=BUCKET):
        keys += [o["Key"] for o in page.get("Contents", []) if run_id in o["Key"]]
    return keys


def main() -> None:
    connect()
    with mlflow.start_run(run_name="from-host") as run:
        mlflow.set_tag("lesson", "16")
        mlflow.log_param("where", "host")
        mlflow.log_metric("answer", 42.0)
        note = TMP / "notes.txt"
        note.write_text(f"run_id={run.info.run_id}\n", encoding="utf-8")
        # s3://... → boto3 trong process này, endpoint = 127.0.0.1:29000 (từ .env)
        mlflow.log_artifact(str(note))

    print(f"\nrun_id       = {run.info.run_id}")
    print(f"artifact_uri = {run.info.artifact_uri}")
    print(f"status       = {mlflow.get_run(run.info.run_id).info.status}")
    print(f"MinIO keys   = {keys_in_minio(run.info.run_id)}")
    print("\nUI → experiment 'mlflow-course-16' → run 'from-host' → tab Artifacts")


if __name__ == "__main__":
    main()
