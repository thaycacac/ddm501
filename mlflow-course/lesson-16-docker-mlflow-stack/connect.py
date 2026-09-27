"""
BÀI 16 — shared connect: đọc cấu hình từ .env, giống tutorial02-extend.

Bài 15: biến S3 nằm cứng trong connect.py (S3_ENV) và bật bằng cờ.
Bài 16: tất cả nằm trong .env; load_dotenv() đưa chúng vào os.environ, rồi
MLflow + boto3 tự đọc từ đó. Mọi script 01–05 của extend mở đầu bằng đúng dòng:
    load_dotenv(dotenv_path=".env")
"""
from __future__ import annotations

import os
from pathlib import Path

import mlflow
from dotenv import load_dotenv

LESSON_DIR = Path(__file__).resolve().parent

# Đường dẫn tuyệt đối → chạy script từ thư mục nào cũng tìm đúng .env.
# (extend dùng ".env" tương đối → phải đứng đúng thư mục tutorial02-extend.)
# Mặc định load_dotenv KHÔNG ghi đè biến đã có sẵn trong terminal.
FOUND_ENV = load_dotenv(LESSON_DIR / ".env")

TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5001")
EXPERIMENT = "mlflow-course-16"
BUCKET = "mlflow"


def connect() -> None:
    if not FOUND_ENV:
        print("CẢNH BÁO: không thấy .env — đã chạy `cp .env.example .env` chưa?")
    mlflow.set_tracking_uri(TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT)
    print(f"tracking_uri = {mlflow.get_tracking_uri()}")
    print(f"s3 endpoint  = {os.getenv('MLFLOW_S3_ENDPOINT_URL', '(chưa có)')}")
    print(f"experiment   = {EXPERIMENT}")
