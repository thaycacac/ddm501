"""
BÀI 15 — Ghép MLflow + Postgres (bài 13) + MinIO (bài 14). Ai upload artifact?

Stack bài này:
  Docker : postgres + minio + minio-init        (copy từ bài 13 + 14)
  Máy bạn: mlflow server (chạy tay như bài 13)  (bài 16 mới đưa vào Docker)

Câu hỏi trung tâm: khi script gọi mlflow.log_artifact(...), AI gửi file lên MinIO?
MLflow có 2 chế độ, khác nhau ở cờ của `mlflow server`:

① DIRECT — cách tutorial02-extend dùng (dòng 60–62 compose của extend)
     mlflow server ... --default-artifact-root s3://mlflow/artifacts

     script ──metadata──▶ MLflow server ──▶ Postgres
     script ──file (boto3, S3 API)──────────────────▶ MinIO     ← CLIENT tự upload

     artifact_uri của run = s3://mlflow/artifacts/<exp_id>/<run_id>/artifacts
     → Server chỉ "chỉ đường". CLIENT cần biết MinIO: endpoint + 2 key (bài 14).
     → Đó là lý do .env.example của extend (dòng 12–17) có MLFLOW_S3_ENDPOINT_URL,
       AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY cho script 01–05.

② PROXY — cách tutorial03 dùng (tutorial03/registry-serving/Dockerfile dòng 18–19)
     mlflow server ... --artifacts-destination s3://mlflow/proxied

     script ──metadata + file (HTTP)──▶ MLflow server ──▶ Postgres
                                                     └──▶ MinIO  ← SERVER upload hộ

     artifact_uri của run = mlflow-artifacts:/<exp_id>/<run_id>/artifacts
     → Client chỉ cần TRACKING_URI, như bài 13. SERVER mới cần key MinIO.

Một điều dễ quên: artifact_location được CHỐT lúc TẠO experiment.
  Đổi cờ server sau đó KHÔNG đổi chỗ lưu của experiment cũ.
  → Bài này dùng 2 experiment riêng: mlflow-course-15-direct, mlflow-course-15-proxy.

File trong bài:
  docker-compose.yml     postgres + minio + minio-init
  connect.py             TRACKING_URI, S3_ENV, use_s3_env(), công cụ soi MinIO
  step1_check_stack.py   gõ cửa 3 mảnh: Postgres, MinIO (bucket mlflow), MLflow
  step2_log_direct.py    chế độ ① — có/không có biến S3 phía client
  step3_log_proxy.py     chế độ ② — client không có biến S3 nào

Thứ tự học: làm theo hướng dẫn trong chat, từng bước một.
"""
print(__doc__)
