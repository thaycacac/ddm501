# =============================================================================
# BÀI 02 — Dockerfile (công thức → docker build → IMAGE của bạn)
# =============================================================================
#
# Luồng:  Dockerfile  --build-->  Image  --run-->  Container
#
# So với Tutorial 02 (ddm501-t02-mlflow/Dockerfile): cùng pattern
#   FROM python:3.11-slim → WORKDIR → COPY → (RUN pip) → CMD [...]
# Ở đây bỏ pip, app chỉ là app.py.
#
# Bạn đọc từng dòng dưới đây, rồi chạy:
#   docker build -t mlflow-course-hello:1 .
#   (xem practice.sh phần B trở đi)
# =============================================================================

# Image nền — layer đầu, bắt buộc.
FROM python:3.11-slim

# ENV = biến môi trường trong image/container (lúc run có thể -e ghi đè).
ENV PYTHONUNBUFFERED=1 \
    PORT=8000

# Mọi path tương đối sau này tính từ /app (như cd /app).
WORKDIR /app

# COPY xảy ra LÚC BUILD — đưa file từ build context (dấu . khi build) vào image.
# Không phải lúc docker run.
COPY app.py .

# EXPOSE chỉ là GHI CHÚ / metadata: "app listen cổng này".
# KHÔNG tự mở port ra máy bạn — vẫn cần: docker run -p HOST:8000 ...
EXPOSE 8000

# CMD = lệnh mặc định khi docker run IMAGE (không ghi thêm command).
# Exec form (JSON): không qua shell, stop signal đúng hơn.
#
# Ghi đè CMD dễ dàng:
#   docker run --rm mlflow-course-hello:1 python --version
# → chạy python --version, KHÔNG chạy app.py.
#
# Khác ENTRYPOINT: xem Dockerfile.entrypoint.
CMD ["python", "app.py"]
