"""
BÀI 15 — Bước 2: chế độ ① DIRECT (cách của tutorial02-extend).

Server bật với:  --default-artifact-root s3://mlflow/artifacts
→ artifact_uri của run là s3://... → CHÍNH script này gọi boto3 upload lên MinIO.

  python step2_log_direct.py                  # client KHÔNG có biến S3 → hỏng
  python step2_log_direct.py --with-s3-env    # client có 3 biến S3   → được

Khi hỏng: run VẪN có trong Postgres (param/metric đã gửi trước đó), status
FAILED, nhưng không có file nào — một run "nửa vời".
"""
from __future__ import annotations

import argparse
from pathlib import Path

import mlflow

from connect import EXPERIMENT_DIRECT, connect, minio_keys_of_run, use_s3_env

TMP = Path(__file__).resolve().parent / "_tmp"
TMP.mkdir(exist_ok=True)


def log_one_run() -> None:
    with mlflow.start_run(run_name="direct") as run:
        mlflow.log_param("mode", "direct")   # HTTP → server → Postgres
        mlflow.log_metric("answer", 42.0)    # HTTP → server → Postgres
        print(f"run_id       = {run.info.run_id}")
        print(f"artifact_uri = {run.info.artifact_uri}")

        note = TMP / "notes.txt"
        note.write_text(f"run_id={run.info.run_id}\n", encoding="utf-8")
        # artifact_uri bắt đầu bằng s3:// → MLflow chọn S3ArtifactRepository
        # → boto3 chạy NGAY TRONG PROCESS NÀY, đọc MLFLOW_S3_ENDPOINT_URL + AWS_*
        mlflow.log_artifact(str(note))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--with-s3-env", action="store_true",
                    help="đặt 3 biến S3 (connect.S3_ENV) cho process này")
    args = ap.parse_args()

    if args.with_s3_env:
        use_s3_env()
    connect(EXPERIMENT_DIRECT)
    print()

    try:
        log_one_run()
    except Exception as exc:
        print(f"\nLỖI khi log: {type(exc).__name__}: {str(exc)[:200]}")

    # Run vừa rồi (kể cả khi lỗi — `with start_run` đã đóng nó với status FAILED)
    run = mlflow.last_active_run()
    if run is None:
        print("Chưa tạo được run nào — MLflow server có đang chạy ở :5001 không?")
        return
    print(f"\nstatus trong Postgres = {run.info.status}")
    print(f"params                = {run.data.params}")
    keys = minio_keys_of_run(run.info.run_id)
    print(f"file trong MinIO      = {keys or '(không có)'}")


if __name__ == "__main__":
    main()
