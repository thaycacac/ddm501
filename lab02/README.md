# Tutorial 02-02 — The full MLflow stack

**DDM501 — AI in DevOps, DataOps, MLOps

Between Tutorial 02 and Tutorial 03, after 02-01. Same model, same trainer, same API. The changes are: Postgres holds the metadata, MinIO holds the artefacts.

## What runs

| Service | Image | Job |
|---|---|---|
| `postgres` | `postgres:16-alpine` | Backend store — runs, params, metrics, registry |
| `minio` | `minio/minio` | Artifact store — the pickles, S3 protocol |
| `createbucket` | this project | Creates the bucket once, then exits |
| `mlflow` | this project | Tracking server, holds no data of its own |
| `api` | this project | Serves `models:/<name>/<version>` |
| `trainer` | this project | Trains and registers, on demand |

## Setup

```bash
docker compose up -d --build
docker compose ps                 # mlflow healthy in about a minute
```

| | Where |
|---|---|
| MLflow UI | <http://127.0.0.1:15020> |
| MinIO console | <http://127.0.0.1:19011> — login from `.env` |
| Postgres | `psql -h localhost -p 15432 -U mlflow` |
| API | <http://127.0.0.1:18012/docs> |

On Linux, set `UID_GID` in `.env` to what `id -u` prints first.

## Register

```bash
docker compose run --rm trainer python scripts/train_and_register.py
```

Registers `breast-cancer-classifier` version 1, ROC AUC 0.9932. Run it again
for version 2.

Now look at both halves. In MinIO you will find
`mlflow/1/<run-id>/artifacts/model/model.pkl`. In Postgres:

```bash
docker compose exec postgres psql -U mlflow -d mlflow \
  -c "select name, version, source from model_versions;"
```

The `source` column is an `s3://` URI. The database stores a pointer; the bytes
live in object storage. Separating them is the whole point of this stack.

## Serve

```bash
docker compose restart api        # reads MODEL_VERSION from .env at start-up
curl -s localhost:18012/health
```

```json
{"status":"ok","model_loaded":true,"model_uri":"models:/breast-cancer-classifier/1"}
```

```bash
docker compose run --rm -T trainer python scripts/sample_request.py > sample_request.json
curl -s -X POST localhost:18012/predict \
  -H 'content-type: application/json' -d @sample_request.json
```

## Switch version

Register a second model, set `MODEL_VERSION=2` in `.env`, then:

```bash
docker compose restart api
curl -s localhost:18012/health
```