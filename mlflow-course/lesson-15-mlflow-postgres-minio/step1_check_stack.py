"""
BÀI 15 — Bước 1: stack giờ có 3 mảnh. Có lỗi thì câu hỏi đầu tiên: mảnh nào chết?

  [1] Postgres   127.0.0.1:25432         (metadata — bài 13)
  [2] MinIO      127.0.0.1:29000         (file — bài 14), có bucket "mlflow" chưa?
  [3] MLflow     127.0.0.1:5001/health   (cửa chính của script)

Mỗi mảnh kiểm riêng, in OK/FAIL, không dừng ở mảnh lỗi đầu tiên.
"""
from __future__ import annotations

import urllib.request

import boto3
import psycopg2

from connect import BUCKET, PG, S3_ENV, TRACKING_URI


def check_postgres() -> str:
    with psycopg2.connect(**PG, connect_timeout=3) as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM information_schema.tables "
                    "WHERE table_schema = 'public'")
        n_tables = cur.fetchone()[0]
    conn.close()
    # 0 bảng = Postgres sống nhưng MLflow chưa từng khởi động với DB này
    return f"{n_tables} bảng"


def check_minio() -> str:
    s3 = boto3.client(
        "s3",
        endpoint_url=S3_ENV["MLFLOW_S3_ENDPOINT_URL"],
        aws_access_key_id=S3_ENV["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=S3_ENV["AWS_SECRET_ACCESS_KEY"],
    )
    buckets = [b["Name"] for b in s3.list_buckets()["Buckets"]]
    if BUCKET not in buckets:
        # Sống nhưng thiếu bucket → minio-init chưa chạy / chạy lỗi (bài 14 bước 3)
        raise RuntimeError(f"thiếu bucket '{BUCKET}', đang có {buckets}")
    return f"buckets = {buckets}"


def check_mlflow() -> str:
    body = urllib.request.urlopen(f"{TRACKING_URI}/health", timeout=3).read().decode()
    return f"/health -> {body!r}"


def main() -> None:
    for name, check in [("Postgres", check_postgres),
                        ("MinIO", check_minio),
                        ("MLflow", check_mlflow)]:
        try:
            print(f"{name:<9} OK    {check()}")
        except Exception as exc:
            print(f"{name:<9} FAIL  {type(exc).__name__}: {str(exc)[:120]}")


if __name__ == "__main__":
    main()
