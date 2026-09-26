# Tutorial 02 — MLflow: tracking, registry, versioning

**DDM501 — AI in DevOps, DataOps, MLOps · FSB, FPT University**

## Before you start

Do Tutorial 01 first. This tutorial is written as the answer to it.

## Setup

Python 3.11 or above.

```bash
python3.11 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Start the server in its own terminal and leave it running:

```bash
mlflow server \
  --backend-store-uri sqlite:///mlflow.db \
  --artifacts-destination ./mlartifacts \
  --host 127.0.0.1 --port 5000
```

Open <http://127.0.0.1:5000>. Port 5000 is the same port Lab 2 uses for MLflow

The SQLite backend is not optional.

## The four steps

Run them in order, from a second terminal, with the server still up.

| Script | What it does | Runtime |
|---|---|---|
| `scripts/step1_track.py` | 12 configurations logged as runs: params, metrics, tags, artifacts, model |
| `scripts/step2_compare.py` | Reads the server back. Answers Tutorial 01's questions. Trains nothing. |
| `scripts/step3_register.py` | Registry: two versions, aliases, and a promotion that moves no files |
| `scripts/step4_load_and_verify.py` | Loads by alias, walks the lineage back to the run, reproduces the logged score |

```bash
export PYTHONPATH=scripts        # Windows PowerShell: $env:PYTHONPATH="scripts"
python scripts/step1_track.py
python scripts/step2_compare.py
python scripts/step3_register.py
python scripts/step4_load_and_verify.py
```

Keep the UI open while you run them.

## Running it in Docker instead

Optional, and it replaces the venv — do not run both servers at once against
the same data. Everything lives in `Dockerfile` and `docker-compose.yml`.

```bash
docker compose up -d --build     # first time: builds the image, then starts the server
docker compose ps                # wait for STATUS = healthy, about 40 seconds
```

Open <http://127.0.0.1:15000>. Then run the same four steps, each in its own
throwaway container:

```bash
docker compose run --rm runner python scripts/step1_track.py
docker compose run --rm runner python scripts/step2_compare.py
docker compose run --rm runner python scripts/step3_register.py
docker compose run --rm runner python scripts/step4_load_and_verify.py

docker compose down              # stop everything; mlflow-data/ survives
```

On Linux, before the first `up`, copy `.env.example` to `.env` and put your own
uid in it — otherwise the container writes to `mlflow-data/` as root and you
will need `sudo` to clean up afterwards. macOS and Windows can skip that.

```bash
export MLFLOW_TRACKING_URI=http://127.0.0.1:15000
python scripts/step1_track.py
```