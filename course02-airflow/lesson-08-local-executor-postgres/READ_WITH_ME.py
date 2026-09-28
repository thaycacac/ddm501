"""
BÀI 08 — Airflow kiểu production: Postgres + LocalExecutor + service tách riêng
         (= tutorial07/docker-compose.yml dòng 1–46 và 296–349, tutorial07/airflow/init_airflow.sh,
            tutorial07/airflow/Dockerfile)

1) Các thành phần của Airflow

   webserver   UI + REST API, đọc metadata DB, đọc file log. KHÔNG chạy task.
   scheduler   đọc DAG, quyết định task nào tới lượt, giao cho EXECUTOR.
   executor    nằm trong scheduler; quyết định task chạy Ở ĐÂU.
   metadata DB dag_run, task_instance, xcom, variable, connection, user...
   (triggerer  chỉ cần cho deferrable operator; tutorial07 không có)

   standalone (bài 01–07) = tất cả trong 1 container + SQLite + SequentialExecutor.

2) Executor

   SequentialExecutor  1 task một lúc          dùng được với SQLite (chỉ để học / thử)
   LocalExecutor       nhiều tiến trình con     trong container scheduler — tutorial07
   CeleryExecutor      worker riêng qua Redis/RabbitMQ, scale nhiều máy
   KubernetesExecutor  mỗi task một pod
   SQLite không cho ghi đồng thời → Airflow từ chối LocalExecutor với SQLite. Muốn song song phải có
   Postgres/MySQL. Giới hạn song song: core.parallelism (toàn hệ thống), max_active_tasks của DAG
   (mặc định 16), max_active_runs.

3) Compose của tutorial07

   x-airflow-common: &airflow-common     khuôn chung (image, user, env, volume)
   <<: *airflow-common                   dán khuôn vào service
   environment: {<<: *airflow-common-env, THÊM: ...}
       merge riêng env; ghi "environment:" mà không merge thì env chung bị THAY hết.

   postgres           dùng chung với MLflow: database "mlflow" có sẵn, database "airflow" do init tạo
   airflow-init       chạy 1 lần: CREATE DATABASE nếu chưa có → airflow db migrate → tạo admin
                      restart "no"; chạy lại vô hại (idempotent)
   airflow-webserver  command webserver, port 8080, healthcheck /health
   airflow-scheduler  command scheduler, healthcheck :8974/health (cần ENABLE_HEALTH_CHECK)

   Thứ tự khởi động:
     postgres healthy ──► airflow-init thoát mã 0 ──► webserver + scheduler
     depends_on condition: service_healthy / service_completed_successfully / service_started

   Không dùng /docker-entrypoint-initdb.d để tạo DB airflow: thư mục đó chỉ chạy khi volume Postgres
   còn TRỐNG; volume có sẵn (do MLflow tạo trước) thì không bao giờ chạy lại.

4) Những thứ phải CHUNG giữa webserver và scheduler

   - SQL_ALCHEMY_CONN: cùng một metadata DB
   - thư mục DAG: webserver cũng parse DAG để vẽ Graph/Code
   - thư mục log: task chạy trong scheduler ghi log, webserver đọc để hiển thị
   - WEBSERVER__SECRET_KEY: khác nhau → webserver không lấy được log qua HTTP, UI báo lỗi 403

5) Khác biệt khi đọc tutorial07

   DAGS_ARE_PAUSED_AT_CREATION=false  DAG mới lên là chạy theo lịch ngay (health check 15 phút,
                                      drift mỗi giờ) — không cần unpause như trong khóa này.
   Dockerfile riêng                    thêm mlflow-skinny, scikit-learn, boto3 cho model_retrain,
                                      ghim apache-airflow==2.10.5 cùng lần pip để không bị đổi bản.
   Postgres chung                      user mlflow/mlflow cho cả hai database.

DAG trong bài: lesson08_parallel — 6 task ngủ song song, summary in hostname/pid/thời gian để đo
mức song song thực tế. Metadata giờ nằm trong Postgres → xem trực tiếp bằng psql.

TỔNG KẾT
  - Production tách webserver (UI) và scheduler (lên lịch + LocalExecutor chạy task).
  - SQLite chỉ đi với SequentialExecutor; chạy song song phải có Postgres.
  - airflow-init là job một lần, idempotent: tạo DB → db migrate → tạo admin; các service chờ nó
    bằng service_completed_successfully.
  - YAML anchor giữ config chung một chỗ; env riêng phải merge <<: *airflow-common-env.
  - Webserver và scheduler phải chung DB, DAG, log và SECRET_KEY.
"""
print(__doc__)
