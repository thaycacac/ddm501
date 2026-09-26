# Bài 03 — image cho service trong compose (giống tinh thần T02 Dockerfile).
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PORT=8000 \
    DATA_DIR=/data

WORKDIR /app
COPY app.py .

EXPOSE 8000
CMD ["python", "app.py"]
