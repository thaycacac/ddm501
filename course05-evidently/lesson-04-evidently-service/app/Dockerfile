# Python 3.10: numpy 1.24.3 (đi cùng evidently 0.4.26) không có wheel cho 3.12
FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# copy requirements trước code → sửa main.py không phải cài lại thư viện (tận dụng cache layer)
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY main.py .
RUN mkdir -p /app/reports /app/reference

EXPOSE 8001

# healthcheck bằng Python có sẵn thay vì cài thêm curl
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health', timeout=3)"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
