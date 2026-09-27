"""
BÀI 16 — Docker hóa MLflow server: stack 4 service = tutorial02-extend/docker-compose.yml

Bài 15 bạn gõ tay:
  MLFLOW_S3_ENDPOINT_URL=http://127.0.0.1:29000 AWS_ACCESS_KEY_ID=minio ... \
  mlflow server --backend-store-uri postgresql://mlflow:mlflow@127.0.0.1:25432/mlflow \
                --default-artifact-root s3://mlflow/artifacts --host 127.0.0.1 --port 5001

Bài này biến đúng lệnh đó thành service thứ 4 trong compose. Mỗi mảnh của lệnh
đi về một chỗ:

| Lệnh gõ tay (bài 15)            | Trong Docker (bài 16)                          |
|---------------------------------|------------------------------------------------|
| pip install mlflow psycopg2...  | Dockerfile + requirements.txt (image riêng)    |
| mlflow server ...               | command: của service mlflow                    |
| MLFLOW_S3_ENDPOINT_URL=... env  | environment: của service mlflow                |
| 127.0.0.1:25432 (Postgres)      | postgres:5432   ← tên service, port TRONG mạng |
| 127.0.0.1:29000 (MinIO)         | minio:9000      ← tên service, port TRONG mạng |
| --host 127.0.0.1 --port 5001    | --host 0.0.0.0 --port 5000 + ports "5001:5000" |
| "đợi Postgres/MinIO lên rồi bật"| depends_on + condition                         |
| mở UI xem sống chưa             | healthcheck /health                            |

Mới trong bài này (chưa gặp ở bài 13–15):
  - .env có HAI người đọc:
      docker compose  → thay ${POSTGRES_PORT:-25432} ... trong docker-compose.yml
      script Python   → load_dotenv() lấy MLFLOW_TRACKING_URI, biến S3
  - depends_on 3 điều kiện: service_healthy / service_completed_successfully
  - networks khai báo tường minh (extend dòng 129–132)
  - --host 0.0.0.0: trong container, 127.0.0.1 chỉ là chính container đó

Ánh xạ vào tutorial02-extend:
  Dockerfile              ↔ tutorial02-extend/Dockerfile
  docker-compose.yml      ↔ tutorial02-extend/docker-compose.yml (cả file)
  .env.example            ↔ tutorial02-extend/.env.example

File trong bài:
  Dockerfile, requirements.txt   image cho MLflow server
  docker-compose.yml             4 service: postgres, minio, minio-init, mlflow
  .env.example                   copy thành .env trước khi chạy
  connect.py                     load_dotenv(.env) rồi connect như bài 04–15
  step1_check_stack.py           gõ cửa 3 mảnh từ máy bạn
  step2_log_from_host.py         log 1 run từ máy bạn → Postgres + MinIO

Thứ tự học: làm theo hướng dẫn trong chat, từng bước một.
"""
print(__doc__)
