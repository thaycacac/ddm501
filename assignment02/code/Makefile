.DEFAULT_GOAL := help
SHELL := /bin/bash

-include .env
export

PY ?= .venv/bin/python
AIRFLOW_VENV ?= .venv-airflow
AIRFLOW_HOME ?= $(CURDIR)/.airflow
IMAGE ?= churnguard-train:1.1.0
AIRFLOW_ENV = AIRFLOW_HOME=$(AIRFLOW_HOME) AIRFLOW__CORE__DAGS_FOLDER=$(CURDIR)/dags \
	AIRFLOW__CORE__LOAD_EXAMPLES=False AIRFLOW__CORE__UNIT_TEST_MODE=False

.PHONY: help setup setup-airflow data validate train reproduce test lint format \
	drift drift-sim promote rollback dag-check airflow-test airflow-test-drift \
	docker-build docker-train mlflow-ui clean

help: ## List targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk -F':.*?## ' '{printf "%-15s %s\n", $$1, $$2}'

setup: ## Create .venv and install pinned dependencies
	python3.12 -m venv .venv
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -r requirements-dev.txt

setup-airflow: ## Separate venv with Airflow 2.10.5 (official constraints)
	python3.12 -m venv $(AIRFLOW_VENV)
	$(AIRFLOW_VENV)/bin/pip install "apache-airflow==2.10.5" \
		--constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.10.5/constraints-3.12.txt"

data: ## Download (if missing) + verify sha256 of the raw dataset
	$(PY) -m src.pipeline ingest

validate: data ## Run the data validation gate
	$(PY) -m src.pipeline validate

train: ## Run the whole pipeline: ingest -> ... -> register @challenger (all experiments)
	$(PY) -m src.pipeline all

drift: ## PSI drift check of the current snapshot vs the training reference
	$(PY) -m src.pipeline drift

drift-sim: ## Drift check on a SIMULATED drifted snapshot (exercises the trigger path)
	$(PY) scripts/make_drifted_snapshot.py
	$(PY) -m src.pipeline drift --current data/simulated/drifted_snapshot.csv

promote: ## Human approval: @champion <- @challenger (make promote APPROVER="Name")
	@test -n "$(APPROVER)" || (echo "APPROVER is required" && exit 1)
	$(PY) -m src.pipeline promote --approved-by "$(APPROVER)"

rollback: ## Restore @champion to @previous_champion (make rollback REASON="...")
	$(PY) -m src.pipeline rollback --reason "$(or $(REASON),manual rollback)"

reproduce: ## Wipe MLflow state, then re-run everything from scratch
	rm -rf mlflow.db mlartifacts reports/pipeline_state data/interim data/processed
	$(MAKE) train

test: ## Unit tests
	$(PY) -m pytest

lint: ## Style + static checks
	$(PY) -m ruff check src tests dags scripts
	$(PY) -m black --check src tests dags scripts

format: ## Auto-format
	$(PY) -m ruff check --fix src tests dags scripts
	$(PY) -m black src tests dags scripts

dag-check: ## Import the DAGs with real Airflow and list import errors
	$(AIRFLOW_ENV) $(AIRFLOW_VENV)/bin/airflow db migrate > /dev/null
	$(AIRFLOW_ENV) $(AIRFLOW_VENV)/bin/airflow dags list-import-errors
	$(AIRFLOW_ENV) $(AIRFLOW_VENV)/bin/airflow dags list
	$(AIRFLOW_ENV) $(AIRFLOW_VENV)/bin/airflow tasks list telco_churn_training --tree
	$(AIRFLOW_ENV) $(AIRFLOW_VENV)/bin/airflow tasks list telco_churn_drift_monitor --tree

airflow-test: dag-check ## Execute one full training DAG run locally (airflow dags test)
	$(AIRFLOW_ENV) TELCO_PYTHON=$(CURDIR)/$(PY) $(AIRFLOW_VENV)/bin/airflow dags test \
		telco_churn_training $$(date +%Y-%m-%d)

airflow-test-drift: ## Drift-monitor DAG run; SNAPSHOT=data/simulated/drifted_snapshot.csv to force drift
	$(AIRFLOW_ENV) TELCO_PYTHON=$(CURDIR)/$(PY) \
		$(if $(SNAPSHOT),TELCO__PATHS__DRIFT_CURRENT_DATA=$(SNAPSHOT)) \
		$(AIRFLOW_VENV)/bin/airflow dags test telco_churn_drift_monitor $$(date +%Y-%m-%d)

docker-build: ## Build the training image (bakes the git commit into it)
	docker build -t $(IMAGE) \
		--build-arg GIT_SHA=$$(git rev-parse HEAD 2>/dev/null || echo unknown) \
		--build-arg GIT_DIRTY=$$(test -z "$$(git status --porcelain -- . 2>/dev/null)" && echo false || echo true) \
		.

docker-train: ## Run the full pipeline inside the container (MLflow state in a volume)
	docker run --rm -v churnguard-mlflow:/app/state \
		-e TELCO__MLFLOW__TRACKING_URI=sqlite:////app/state/mlflow.db \
		-e TELCO__MLFLOW__ARTIFACT_ROOT=/app/state/mlartifacts \
		$(IMAGE) all

mlflow-ui: ## Browse runs and the model registry at http://localhost:5000
	.venv/bin/mlflow ui --backend-store-uri sqlite:///mlflow.db --port 5000

clean: ## Remove caches (keeps MLflow state and data)
	rm -rf .pytest_cache .ruff_cache **/__pycache__
