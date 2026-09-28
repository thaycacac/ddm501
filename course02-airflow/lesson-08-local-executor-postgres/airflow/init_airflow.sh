#!/usr/bin/env bash
# BÀI 08 — Giống tutorial07/airflow/init_airflow.sh.
# Job một lần: tạo database "airflow" trong Postgres dùng chung, migrate schema, tạo user admin.
# Chạy lại bao nhiêu lần cũng được (idempotent) — mỗi lần `docker compose up` service này lại chạy.
set -euo pipefail   # lệnh nào lỗi → dừng ngay, exit khác 0 → webserver/scheduler không start

# Vì sao không dùng /docker-entrypoint-initdb.d của Postgres: thư mục đó CHỈ chạy khi volume dữ liệu
# còn trống (lần đầu). Volume đã có sẵn (vd MLflow tạo trước) thì script SQL không bao giờ chạy lại.
# → Tự kiểm tra rồi CREATE DATABASE ở đây. psycopg2 có sẵn trong image Airflow.
python - <<'PY'
import os

import psycopg2
from psycopg2 import sql

db_name = os.environ.get("AIRFLOW_DB_NAME", "airflow")
conn = psycopg2.connect(
    host=os.environ.get("POSTGRES_HOST", "postgres"),
    port=int(os.environ.get("POSTGRES_PORT_INTERNAL", "5432")),
    user=os.environ.get("POSTGRES_USER", "mlflow"),
    password=os.environ.get("POSTGRES_PASSWORD", "mlflow"),
    dbname=os.environ.get("POSTGRES_DB", "mlflow"),   # nối vào DB có sẵn để ra lệnh tạo DB khác
)
# CREATE DATABASE không chạy được trong transaction → bật autocommit
conn.autocommit = True
with conn.cursor() as cur:
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
    if cur.fetchone():
        print(f"Database '{db_name}' đã có")
    else:
        # sql.Identifier: quote tên DB đúng cách (không nối chuỗi thẳng vào SQL)
        cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name)))
        print(f"Đã tạo database '{db_name}'")
conn.close()
PY

# Tạo / nâng cấp bảng metadata (dag_run, task_instance, xcom...). Đã mới nhất thì không làm gì.
airflow db migrate

ADMIN_USER="${AIRFLOW_ADMIN_USER:-admin}"
# Cột 2 của output plain là username → có rồi thì bỏ qua (users create lần 2 sẽ báo lỗi)
if airflow users list --output plain 2>/dev/null | awk '{print $2}' | grep -qx "${ADMIN_USER}"; then
  echo "User '${ADMIN_USER}' đã có"
else
  airflow users create \
    --username "${ADMIN_USER}" \
    --password "${AIRFLOW_ADMIN_PASSWORD:-admin}" \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email "${AIRFLOW_ADMIN_EMAIL:-admin@example.com}"
fi

echo "Airflow init hoàn tất"
