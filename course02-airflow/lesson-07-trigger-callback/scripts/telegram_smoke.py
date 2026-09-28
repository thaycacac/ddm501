"""
BÀI 07 — Gửi thử 1 tin Telegram bằng CHÍNH util mà DAG dùng, chạy trong container Airflow.

  docker compose exec airflow python /opt/airflow/scripts/telegram_smoke.py

In True = biến môi trường vào container đúng và bot gửi được. Không in token.
"""
import os
import sys

# Giống cách Airflow nạp DAG: thêm thư mục dags/ vào sys.path để import được utils.*
sys.path.insert(0, "/opt/airflow/dags")

from utils.telegram_alert import send_telegram_message  # noqa: E402

print("TELEGRAM_BOT_TOKEN có giá trị:", bool(os.getenv("TELEGRAM_BOT_TOKEN")))
print("TELEGRAM_CHAT_ID:", os.getenv("TELEGRAM_CHAT_ID") or "(trống)")
print("sent =", send_telegram_message("<b>[airflow-course 07]</b> Tin thử từ container Airflow"))
