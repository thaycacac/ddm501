"""
BÀI 01 — Airflow standalone trong Docker + DAG đầu tiên
         (= tutorial04/ddm501-t03-airflow/Dockerfile + docker-compose.yml)

Airflow là gì?
  Bộ điều phối (orchestrator): bạn mô tả "các bước + thứ tự + lịch chạy" bằng
  Python, Airflow tự chạy đúng giờ, đúng thứ tự, thử lại khi lỗi, giữ log từng bước.

Từ vựng cốt lõi:
  DAG       một pipeline = đồ thị có hướng, không vòng (Directed Acyclic Graph).
            Là MỘT FILE PYTHON đặt trong thư mục dags/.
  Task      một bước trong DAG (một hàm Python, một lệnh bash...).
  DAG run   một lần chạy DAG (ví dụ: lần chạy cho ngày 2026-09-27).
  Task instance  một task trong một DAG run → có trạng thái + log riêng.

Bên trong Airflow có 4 mảnh:

  dags/*.py ──(đọc định kỳ)──► SCHEDULER ──(ghi trạng thái)──► METADATA DB
                                  │                              ▲
                                  ▼                              │
                              EXECUTOR  ── chạy task ────────────┘
                                                                 ▲
  bạn ──► WEBSERVER (UI :8080) ── đọc DB để vẽ Grid, log ────────┘
          TRIGGERER — chờ sự kiện cho task "deferrable" (chưa dùng trong khóa)

  - Scheduler: parse file DAG, quyết định task nào tới lượt, giao cho executor.
  - Executor : SequentialExecutor = chạy TỪNG task một (bắt buộc khi DB là SQLite).
  - Metadata DB: SQLite trong container (/opt/airflow/airflow.db) — giống vai trò
    backend store của MLflow (bài 06). Production dùng Postgres (bài 13 mlflow-course).
  - "airflow standalone" = bật cả 4 mảnh trong MỘT process.
    Chỉ để học/dev; production tách từng mảnh thành service riêng.
  - Đăng nhập UI: admin / admin (compose tạo sẵn qua biến _AIRFLOW_WWW_USER_*).

Cấu hình bằng biến môi trường:  AIRFLOW__<SECTION>__<KEY>=value
  AIRFLOW__CORE__EXECUTOR=SequentialExecutor   ≡  [core] executor = ... trong airflow.cfg
  (Cùng ý tưởng MLFLOW_TRACKING_URI: cấu hình từ ngoài, không sửa code/image.)

Đã học ở mlflow-course, gặp lại ở đây:
  build image, ports, bind mount, healthcheck + start_period, user:, restart,
  .dockerignore (bài 01–03, 12, 16, capstone T03).

File trong bài:
  Dockerfile          image airflow-course:2.8.4 (Airflow + pandas + pyarrow)
  .dockerignore       build không cần gửi file nào
  docker-compose.yml  1 service "airflow" chạy standalone, UI ở :28080
  dags/hello_dag.py   DAG 2 task: chào, rồi ghi file ra data/staging/

Thứ tự học: làm theo hướng dẫn trong chat, từng bước một.
"""
print(__doc__)
