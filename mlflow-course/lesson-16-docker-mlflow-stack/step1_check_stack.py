"""
BÀI 16 — kiểm tra 3 cửa mà MÁY BẠN dùng để nói chuyện với stack.

  [1] MLflow   MLFLOW_TRACKING_URI/health     (từ .env)
  [2] MinIO    MLFLOW_S3_ENDPOINT_URL         (từ .env) — có bucket "mlflow"?
  [3] Postgres 127.0.0.1:POSTGRES_PORT        (từ .env) — chỉ để bài học soi

Cùng một stack, bên TRONG mạng compose dùng địa chỉ khác (postgres:5432,
minio:9000). Script này đứng NGOÀI nên dùng port đã publish.
"""
from __future__ import annotations

import os
import urllib.request

import boto3
import psycopg2

from connect import BUCKET, FOUND_ENV, TRACKING_URI


def check_mlflow() -> str:
    body = urllib.request.urlopen(f"{TRACKING_URI}/health", timeout=3).read().decode()
    return f"{TRACKING_URI}/health -> {body!r}"


def check_minio() -> str:
    # Không truyền key: boto3 tự đọc AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY
    # từ môi trường (load_dotenv đã đặt). endpoint thì boto3 không tự đọc tên
    # MLFLOW_S3_ENDPOINT_URL — đó là tên của MLflow — nên phải truyền tay.
    endpoint = os.environ["MLFLOW_S3_ENDPOINT_URL"]
    s3 = boto3.client("s3", endpoint_url=endpoint)
    buckets = [b["Name"] for b in s3.list_buckets()["Buckets"]]
    if BUCKET not in buckets:
        raise RuntimeError(f"thiếu bucket '{BUCKET}', đang có {buckets}")
    return f"{endpoint} buckets = {buckets}"


def check_postgres() -> str:
    port = int(os.getenv("POSTGRES_PORT", "25432"))
    with psycopg2.connect(host="127.0.0.1", port=port, user="mlflow", password="mlflow",
                          dbname="mlflow", connect_timeout=3) as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM information_schema.tables "
                    "WHERE table_schema = 'public'")
        n_tables = cur.fetchone()[0]
    conn.close()
    return f"127.0.0.1:{port} — {n_tables} bảng"


def main() -> None:
    print(f".env tìm thấy: {FOUND_ENV}\n")
    for name, check in [("MLflow", check_mlflow),
                        ("MinIO", check_minio),
                        ("Postgres", check_postgres)]:
        try:
            print(f"{name:<9} OK    {check()}")
        except Exception as exc:
            print(f"{name:<9} FAIL  {type(exc).__name__}: {str(exc)[:120]}")


if __name__ == "__main__":
    main()
