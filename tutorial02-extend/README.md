# Tutorial 03 — MLflow registry: aliases, load, routing

**DDM501 — AI in DevOps, DataOps, MLOps · FSB, FPT University**

## Before you start

Do Tutorial 01 and Tutorial 02 first. This tutorial uses a full MLflow stack
(PostgreSQL + MinIO/S3 + MLflow server) and walks registry aliases end to end.

## Setup

Python 3.11 or above. Versions match Tutorial 02 / Lab 2 (`mlflow==2.19.0`,
`scikit-learn==1.6.0`).

```bash
cd tutorial03
python3.11 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # adjust ports in .env if they clash
```

## Start the stack (Docker)

Infrastructure runs in Docker. Leave it up while you run the Python scripts.

```bash
docker compose up -d --build
docker compose ps                  # wait until mlflow STATUS = healthy (~40s)
```

MinIO images are pulled from **quay.io** (not Docker Hub). Docker Hub
`minio/minio` often fails with `pull access denied`.

| Service | URL |
|---|---|
| MLflow UI | <http://127.0.0.1:5001> |
| MinIO console | <http://127.0.0.1:9001> (user `minio` / pass `minio123`) |

Port **5001** (not 5000) avoids clash with Tutorial 02 and macOS AirPlay Receiver.

Client scripts read `MLFLOW_TRACKING_URI` and S3 settings from `.env`.
Artifacts go to MinIO (`s3://mlflow/artifacts`); metadata lives in Postgres.

## The five steps

Run them in order, from a second terminal, with the stack still up and the
venv activated.

| Script | What it does |
|---|---|
| `01_training.py` | Train two Random Forests, log runs, register versions **1** and **2** |
| `02_update_models.py` | Update description + tags on version **2** |
| `03_configuration_alias.py` | Set aliases `dev` / `staging` / `prod`, promote `dev` → `staging` |
| `04_loading_models.py` | Load by alias (`@dev`) and by version (`/2`) |
| `05_model_routing.py` | Simulate traffic split: ~90% `prod`, ~10% `dev` |

```bash
python 01_training.py
python 02_update_models.py
python 03_configuration_alias.py
python 04_loading_models.py
python 05_model_routing.py
```

Keep the MLflow UI open while you run them — Models → `breast_cancer-predictor`
shows versions and aliases.

After a **fresh** `01_training.py`, you only have versions 1 and 2. The later
scripts are wired to those versions. Re-running `01` creates new version numbers;
update the version strings in `02`–`04` (or wipe the stack volumes) if you need
a clean start.

## Tear down

```bash
docker compose down                # stop containers; named volumes keep data
docker compose down -v             # also delete Postgres / MinIO / MLflow volumes
```

## Port clashes

Postgres is published on host port **15432** (a local Postgres usually owns 5432).
If something already owns 15432 / 9000 / 9001 / 5001, change the matching
`*_PORT` values in `.env` and set `MLFLOW_TRACKING_URI` /
`MLFLOW_S3_ENDPOINT_URL` to the same host ports.
