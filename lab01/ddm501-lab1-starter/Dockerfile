# =============================================================================
# Credit Default Risk Scoring API
# DDM501 - Lab 1: First ML Product
# =============================================================================
FROM python:3.11-slim

# TODO 1: environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# TODO 2: working directory
WORKDIR /app

# TODO 3: install dependencies first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# TODO 4: application code (models/ is mounted at runtime)
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY data/ ./data/

# TODO 5: non-root user
RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/models \
    && chown -R appuser:appuser /app
USER appuser

# TODO 6: expose port
EXPOSE 8000

# TODO 7: health check — require model_loaded true
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request, json; data=json.load(urllib.request.urlopen('http://127.0.0.1:8000/health')); assert data.get('model_loaded') is True"

# TODO 8: bind uvicorn to 0.0.0.0
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
