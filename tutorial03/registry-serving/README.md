# Tutorial 02-01 — Serving from the registry

**DDM501 — AI in DevOps, DataOps, MLOps

Between Tutorial 02 and Tutorial 03. Tutorial 02 registered models. This one
serves one, and the API never sees a model file: it asks the registry for a
name and a version.

## Setup

```bash
docker compose up -d --build
docker compose ps                 # mlflow healthy in about 40 seconds
```

MLflow UI at <http://127.0.0.1:15010>. The API is up too, and reports itself
degraded — nothing is registered yet.

On Linux, set `UID_GID` in `.env` to what `id -u` prints first.

## Register

```bash
docker compose run --rm trainer python scripts/train_and_register.py
```

Trains the Tutorial 01 model and registers it as
`breast-cancer-classifier` version 1, ROC AUC 0.9932. Run it again and you get
version 2 — registering never overwrites.

## Serve

The API reads `.env` at start-up:

```
MODEL_NAME=breast-cancer-classifier
MODEL_VERSION=1
```

```bash
docker compose restart api
curl -s localhost:18011/health
```

```json
{"status":"ok","model_loaded":true,"model_uri":"models:/breast-cancer-classifier/1"}
```

## Predict

```bash
docker compose run --rm -T trainer python scripts/sample_request.py > sample_request.json
curl -s -X POST localhost:18011/predict \
  -H 'content-type: application/json' -d @sample_request.json
```

```json
{"prediction":"malignant","probability_benign":0.0,
 "served_by":"models:/breast-cancer-classifier/1"}
```

## Switch version

Register a second model, then change one line:

```bash
docker compose run --rm trainer python scripts/train_and_register.py
# set MODEL_VERSION=2 in .env
docker compose restart api
curl -s localhost:18011/health
```

`model_uri` now ends in `/2`