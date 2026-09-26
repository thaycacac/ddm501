# Credit Default Risk Scoring API

DDM501 Lab 1 — FastAPI service that scores credit-card default risk and turns the probability into an underwriting decision.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Dataset ships in data/credit_default.csv; train once:
python scripts/train_model.py

uvicorn app.main:app --reload
```

- Swagger UI: http://localhost:8000/docs
- Health: `GET /health`
- Score one: `POST /predict`
- Score many: `POST /predict/batch`
- Model metadata: `GET /model/info`

## Decision rule

Thresholds come from environment variables (`REVIEW_THRESHOLD`, `DECLINE_THRESHOLD`; defaults 0.30 / 0.60):

| Probability | Risk band | Decision |
|-------------|-----------|----------|
| `< 0.30` | LOW | APPROVE |
| `0.30 … < 0.60` | MEDIUM | REVIEW |
| `≥ 0.60` | HIGH | DECLINE |

## Docker

Model artifact is **not** baked into the image. Compose mounts `./models` read-only:

```bash
python scripts/train_model.py   # produces models/credit_model.joblib
docker compose up --build
docker inspect --format='{{.State.Health.Status}}' credit-risk-api
```

## Tests

```bash
pytest tests/ -v --cov=app --cov-report=term-missing
```

## Project layout

- `app/` — FastAPI app, Pydantic contract, model wrapper, config
- `scripts/train_model.py` — train HistGradientBoosting pipeline
- `models/` — runtime artifact (mounted in Compose)
- `tests/` — API, validation, behaviour, batch coverage
