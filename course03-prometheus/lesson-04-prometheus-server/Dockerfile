# Image cho service của bài 03 (= tutorial06/Dockerfile).
# Build context là ../lesson-03-instrument-fastapi (xem docker-compose.yml), nên các
# lệnh COPY dưới đây lấy file từ thư mục bài 03.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# requirements của khóa nằm ở ../requirements.txt, ngoài build context → liệt kê trực tiếp.
RUN pip install --no-cache-dir \
    fastapi==0.115.6 "uvicorn[standard]==0.34.0" pydantic==2.10.4 \
    scikit-learn==1.6.0 numpy==2.2.1 pandas==2.2.3 joblib==1.4.2 \
    prometheus-client==0.21.1

COPY app/ ./app/
COPY scripts/ ./scripts/
COPY data/ ./data/

# Train NGAY LÚC BUILD: file pickle được tạo bởi đúng bản scikit-learn cài ở layer trên.
# Copy model train trên máy vào image dễ gặp lỗi lệch version khi joblib.load.
RUN python scripts/train_model.py && test -f models/model.joblib

# Không chạy bằng root: container bị chiếm quyền cũng không có quyền root.
RUN useradd --create-home --uid 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# HEALTHCHECK hỏi /health và chỉ coi là khỏe khi model_loaded = true — không phải chỉ
# "process còn sống". docker-compose dùng trạng thái này cho depends_on: service_healthy.
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys,json; \
r=urllib.request.urlopen('http://localhost:8000/health',timeout=4); \
sys.exit(0 if json.load(r)['model_loaded'] else 1)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
