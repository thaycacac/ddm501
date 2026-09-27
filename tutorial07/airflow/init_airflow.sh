#!/usr/bin/env bash
# One-shot init for Airflow: create the metadata DB inside the shared Postgres,
# migrate the schema and create the admin user. Safe to re-run.
set -euo pipefail

# The Postgres volume may already be initialised (docker-entrypoint-initdb.d won't run again),
# so the airflow database is created here instead.
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
    dbname=os.environ.get("POSTGRES_DB", "mlflow"),
)
conn.autocommit = True
with conn.cursor() as cur:
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
    if cur.fetchone():
        print(f"Database '{db_name}' already exists")
    else:
        cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name)))
        print(f"Created database '{db_name}'")
conn.close()
PY

airflow db migrate

ADMIN_USER="${AIRFLOW_ADMIN_USER:-admin}"
if airflow users list --output plain 2>/dev/null | awk '{print $2}' | grep -qx "${ADMIN_USER}"; then
  echo "Admin user '${ADMIN_USER}' already exists"
else
  airflow users create \
    --username "${ADMIN_USER}" \
    --password "${AIRFLOW_ADMIN_PASSWORD:-admin}" \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email "${AIRFLOW_ADMIN_EMAIL:-admin@example.com}"
fi

echo "Airflow init completed"
