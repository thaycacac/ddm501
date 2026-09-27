# Khóa thực hành: Docker + MLflow → Tutorial 02 → Tutorial 02-extend

Ports của khóa:

| Service  | Port khóa học | Ghi chú |
|----------|---------------|---------|
| MLflow   | 5001          | như bài 04–11 (`MLFLOW_TRACKING_URI` ghi đè được). Stack tutorial02-extend cũng dùng 5001 → chỉ bật một trong hai |
| Postgres | 25432         | 5432 bị Postgres trên máy chiếm, 15432 của tutorial02-extend |
| MinIO    | 29000 (API), 29001 (console) | từ bài 14 |

Quy ước mỗi bài: `connect.py` (TRACKING_URI + `EXPERIMENT = "mlflow-course-NN"`),
compose `name: mlflow-course-NN`, container `mlflow-course-NN-<service>`, file tạm trong `_tmp/`.

Từ bài 16 (bước 4) trở đi: chỉ học **happy case** — không còn thực hành cố ý làm hỏng
(quên `.env`, quên bật service, sai key...).

## Roadmap

Mục tiêu cuối: đọc và giải thích được **từng dòng** của `../tutorial02-extend`.
Mỗi bài dựng thêm MỘT mảnh, tự viết từ đầu trong thư mục bài học. Bài chỉ được
tạo khi bạn học xong bài trước.

| Bài | Chủ đề | Ánh xạ vào tutorial02-extend | Status |
|-----|--------|------------------------------|--------|
| 01–12 | Docker + MLflow core, Docker hóa MLflow (SQLite) | — | Xong |
| Capstone T02 | Tutorial 02 end-to-end | `../tutorial02/ddm501-t02-mlflow` | Xong |
| 13 | Postgres làm backend store (thay SQLite) | service `postgres`, `--backend-store-uri` | Xong |
| 14 | MinIO: kho file kiểu S3 tự host, bucket, boto3, init container | service `minio`, `minio-init` | Xong |
| 15 | Ghép MLflow + Postgres + MinIO; ai upload artifact? | `--default-artifact-root s3://…`, biến S3 trong `.env` | Xong |
| 16 | Docker hóa MLflow server: 4 service, `depends_on`, healthcheck, network, `.env` | `Dockerfile`, `docker-compose.yml`, `.env.example` | Xong |
| 17 | Train + log + register có signature / input_example (chạy trên stack bài 16) | `01_training.py`, `utils/data.py` | Xong |
| 18 | Sửa metadata version + alias `dev`/`staging`/`prod`, promote (dùng model bài 17) | `02_update_models.py`, `03_configuration_alias.py` | Xong |
| **19** | Load theo alias/version + chia traffic A/B (dùng alias bài 18) | `04_loading_models.py`, `05_model_routing.py` | **Đang học** |
| Capstone extend | Chạy 01→05, giải thích từng dòng, tìm chỗ sai trong code gốc | toàn bộ `../tutorial02-extend` | Chưa tạo |

## Bài đang học

```bash
cd lesson-19-load-routing
python READ_WITH_ME.py
```
