# Training image: runs the full pipeline (or a single stage) reproducibly.
FROM python:3.12.11-slim-bookworm

# Code version baked into the image and logged as the `git_sha` run tag.
ARG GIT_SHA=unknown
ARG GIT_DIRTY=unknown

ENV PYTHONDONTWRITEBYTECODE=1 \
    TELCO_GIT_SHA=${GIT_SHA} \
    TELCO_GIT_DIRTY=${GIT_DIRTY} \
    GIT_PYTHON_REFRESH=quiet \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=42 \
    PIP_NO_CACHE_DIR=1 \
    MLFLOW_DISABLE_AGENT_HINT=1 \
    TELCO_PROJECT_ROOT=/app

# libgomp1: OpenMP runtime required by LightGBM and XGBoost.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY configs/ configs/
COPY src/ src/
COPY data/raw/ data/raw/

RUN useradd --create-home --uid 1000 trainer \
    && mkdir -p /app/state \
    && chown -R trainer /app
USER trainer

ENTRYPOINT ["python", "-m", "src.pipeline"]
CMD ["all"]
