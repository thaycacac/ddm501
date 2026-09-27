# =============================================================================
# BÀI 16 — Dockerfile cho MLflow server
# =============================================================================
# So sánh với tutorial02-extend/Dockerfile. Khác biệt:
#   - extend cài curl: không cần, healthcheck của mlflow dùng python urllib
#   - extend cài cả requirements của script (scikit-learn, pandas...) vào server
#   - extend cài thêm gunicorn: mlflow đã tự kéo gunicorn theo trên Linux
#
# Không có CMD: lệnh `mlflow server ...` nằm ở `command:` trong compose (giống
# extend). Nhờ vậy đổi cờ server chỉ cần sửa compose, không phải build lại image.
# (Tutorial 02 / bài 12 thì để CMD trong Dockerfile — cả hai cách đều đúng.)
# =============================================================================

FROM python:3.11-slim

# PYTHONUNBUFFERED: log in ra ngay → `docker compose logs -f mlflow` thấy liền
# PIP_NO_CACHE_DIR : không giữ cache pip trong image → image nhỏ hơn
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /mlflow

# Copy requirements TRƯỚC, cài xong mới copy thứ khác (bài 02: layer cache).
# Ở đây không có thứ khác — image chỉ cần mlflow và driver.
COPY requirements.txt .
RUN pip install -r requirements.txt

# Chỉ là tài liệu: container nghe 5000. Publish ra máy bạn là việc của `ports:`.
EXPOSE 5000
