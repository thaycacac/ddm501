"""
BÀI 13 — Bước 1: Postgres chỉ là một database bình thường.

Chạy script này HAI lần và so sánh:
  lần 1: sau `docker compose up -d`, TRƯỚC khi bật MLflow  → DB trống
  lần 2: SAU khi bật `mlflow server` dùng Postgres         → có ~20 bảng do MLflow tạo
"""
from __future__ import annotations

import psycopg2

from connect import PG


def main() -> None:
    try:
        conn = psycopg2.connect(**PG, connect_timeout=5)
    except psycopg2.OperationalError as exc:
        print(f"KHÔNG kết nối được Postgres: {exc}".strip())
        print("→ Đã chạy `docker compose up -d` trong thư mục bài 13 chưa? "
              "`docker compose ps` có thấy (healthy) không?")
        return

    with conn, conn.cursor() as cur:
        cur.execute("SELECT version()")
        print("server :", cur.fetchone()[0].split(",")[0])

        # information_schema = "danh bạ" chuẩn SQL: DB nào cũng có, liệt kê bảng
        cur.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' ORDER BY table_name"
        )
        tables = [row[0] for row in cur.fetchall()]
    conn.close()

    print(f"số bảng: {len(tables)}")
    for name in tables:
        print(f"  - {name}")
    if not tables:
        print("DB trống — MLflow chưa từng kết nối vào đây.")
    else:
        # MLflow tự tạo bảng (chạy "migration") khi server khởi động lần đầu
        # với một DB trống. alembic_version ghi lại schema đang ở phiên bản nào.
        print("Các bảng trên do MLflow tự tạo lúc khởi động.")


if __name__ == "__main__":
    main()
