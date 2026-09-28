"""
BÀI 14 — shared connect: WHERE = MinIO (S3 API). Bài này chưa dùng MLflow.

boto3 cần đúng 3 thứ để nói chuyện với một kho S3:
  endpoint_url           ĐI ĐÂU     (bỏ trống → mặc định AWS S3 thật)
  aws_access_key_id      AI         (= MINIO_ROOT_USER trong compose)
  aws_secret_access_key  MẬT KHẨU   (= MINIO_ROOT_PASSWORD trong compose)

Tên biến môi trường chọn đúng tên MLflow sẽ đọc ở bài 15:
  MLFLOW_S3_ENDPOINT_URL, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
"""
from __future__ import annotations

import os

import boto3

S3_ENDPOINT = os.getenv("MLFLOW_S3_ENDPOINT_URL", "http://127.0.0.1:29000")
ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID", "minio")
SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "minio123")
BUCKET = "course-14"


def s3_client(endpoint: str | None = S3_ENDPOINT,
              access_key: str = ACCESS_KEY,
              secret_key: str = SECRET_KEY):
    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )
    # client.meta.endpoint_url = địa chỉ boto3 THỰC SỰ sẽ gọi
    print(f"s3 endpoint  = {client.meta.endpoint_url}")
    print(f"access key   = {access_key}")
    return client
