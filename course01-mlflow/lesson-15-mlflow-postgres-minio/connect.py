"""
BÀI 15 — shared connect (server :5001 như bài 04–13).

WHERE = tracking URI | WHICH = experiment name
Thêm so với bài 13: S3_ENV — 3 biến boto3 cần (bài 14). Script KHÔNG tự đặt
chúng; chỉ khi bạn gọi use_s3_env() (cờ --with-s3-env) thì mới có. Như vậy bạn
thấy rõ lúc nào client cần biết MinIO, lúc nào không.
"""
from __future__ import annotations

import os

import boto3
import mlflow

TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5001")
EXPERIMENT_DIRECT = "mlflow-course-15-direct"
EXPERIMENT_PROXY = "mlflow-course-15-proxy"

# Đúng 3 biến trong tutorial02-extend/.env.example (dòng 13, 15, 16).
# MLflow đọc chúng rồi truyền cho boto3 khi upload/download artifact s3://...
S3_ENV = {
    "MLFLOW_S3_ENDPOINT_URL": "http://127.0.0.1:29000",
    "AWS_ACCESS_KEY_ID": "minio",
    "AWS_SECRET_ACCESS_KEY": "minio123",
}
BUCKET = "mlflow"

PG = {"host": "127.0.0.1", "port": 25432, "user": "mlflow",
      "password": "mlflow", "dbname": "mlflow"}


def use_s3_env() -> None:
    for key, value in S3_ENV.items():
        os.environ.setdefault(key, value)


def connect(experiment: str) -> None:
    mlflow.set_tracking_uri(TRACKING_URI)
    mlflow.set_experiment(experiment)
    print(f"tracking_uri = {mlflow.get_tracking_uri()}")
    print(f"experiment   = {experiment}")
    print(f"s3 endpoint  = {os.environ.get('MLFLOW_S3_ENDPOINT_URL', '(client KHÔNG có biến S3)')}")


def minio_keys_of_run(run_id: str) -> list[str]:
    """Chỉ dùng cho BÀI HỌC: soi thẳng MinIO xem file của run nằm ở key nào."""
    s3 = boto3.client(
        "s3",
        endpoint_url=S3_ENV["MLFLOW_S3_ENDPOINT_URL"],
        aws_access_key_id=S3_ENV["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=S3_ENV["AWS_SECRET_ACCESS_KEY"],
    )
    keys = []
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=BUCKET):
        keys += [obj["Key"] for obj in page.get("Contents", []) if run_id in obj["Key"]]
    return keys
