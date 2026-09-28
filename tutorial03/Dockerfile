FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /work

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY scripts/ ./scripts/
COPY app/ ./app/

# Overridden per service in docker-compose.yml.
CMD ["mlflow", "server", \
     "--backend-store-uri", "sqlite:////work/mlflow-data/mlflow.db", \
     "--serve-artifacts", \
     "--artifacts-destination", "file:///work/mlflow-data/mlartifacts", \
     "--host", "0.0.0.0", \
     "--port", "5000"]
