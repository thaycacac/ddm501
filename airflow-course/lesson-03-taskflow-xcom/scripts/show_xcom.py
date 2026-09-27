"""
BÀI 03 — Đọc thẳng bảng xcom trong metadata DB (SQLite).

Chạy TRONG container (file DB nằm trong container):
  docker compose exec airflow python /opt/airflow/scripts/show_xcom.py

Giống bài 13 mlflow-course: nhìn vào DB để thấy dữ liệu nằm đâu.
"""
import sqlite3

DB = "/opt/airflow/airflow.db"

conn = sqlite3.connect(DB)
rows = conn.execute(
    "SELECT run_id, task_id, key, value FROM xcom "
    "WHERE dag_id = 'lesson03_xcom' ORDER BY timestamp"
).fetchall()
conn.close()

print(f"{len(rows)} dòng trong bảng xcom cho lesson03_xcom\n")
for run_id, task_id, key, value in rows:
    # value lưu dạng bytes JSON (BLOB) → decode để đọc
    text = value.decode("utf-8") if isinstance(value, bytes) else value
    print(f"{run_id[:30]:<30} {task_id:<10} {key:<13} {len(value):>4} bytes  {text}")
