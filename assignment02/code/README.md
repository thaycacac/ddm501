# ChurnGuard — MLflow + Airflow training pipeline (Telco Customer Churn)

Companion code for **DDM501 Individual Assignment 2** (ML Pipeline Design & MLOps Analysis).
It implements the training half of **ChurnGuard**, the churn-prediction system designed in
Assignment 1: rank customers by churn risk so a retention call centre that can contact at most
20% of the base per cycle spends its budget where it saves the most revenue.

Every number in `reports/` was produced by this code and is traceable to an MLflow run
(`run_id` column in `reports/experiments.csv`). The report tables in
`../report/A2_report.md` are generated from the same CSV (`../report/scripts/make_tables.py`).

## Layout

```
configs/config.yaml               all defaults (env-var overridable): business assumptions, gates, drift, experiment matrix
src/config.py                     YAML loader + TELCO__SECTION__KEY overrides + global seeding
src/data.py                       ingest (download + sha256 pin), clean, stratified 60/20/20 split
src/validation.py                 raw-data quality gate (schema, domains, ranges, missing, churn rate)
src/features.py                   FeatureEngineer transformer (shared by training and serving), encoders; gender excluded
src/train.py                      model factory + MLflow-tracked training (params, metrics, plots, model, lineage tags)
src/evaluate.py                   ROC/PR-AUC, Recall@top-20%, business cost, capacity-capped threshold, fairness gaps, export
src/register.py                   gates + simplicity rule -> @challenger; human promote; rollback
src/drift.py                      PSI drift check of a customer snapshot vs the training reference
src/pipeline.py                   CLI: one sub-command per stage + drift / promote / rollback
dags/telco_churn_training_dag.py  training DAG (ingest -> validate -> preprocess -> features -> train -> evaluate -> register)
dags/telco_churn_drift_dag.py     weekly drift monitor; publishes a Dataset event that triggers retraining
dags/churnguard_common.py         shared default_args, failure/retry callbacks, webhook alert, stage_task factory
tests/                            pytest (36 tests): validation, features, config overrides, metrics, selection, drift
reports/experiments.csv           MLflow export of the latest pipeline execution (single source for results tables)
reports/gate_report.csv           pass/fail of every gate for every run
reports/challenger.json           latest automatically registered candidate
reports/champion.json             latest promote / rollback action on @champion
reports/drift_report.json         latest drift check
reports/ops_evidence/             Airflow, reproducibility, drift and Docker evidence logs
reports/figures/                  run comparison charts + challenger confusion matrix, ROC/PR, feature importance
Dockerfile, Makefile, requirements*.txt, .env.example, pyproject.toml (ruff/black/pytest config)
```

## Quick start

```bash
make setup                 # .venv with pinned requirements (Python 3.12)
make train                 # full pipeline: 16 MLflow runs, gates, register @challenger
make test lint             # pytest + ruff + black --check
make mlflow-ui             # http://localhost:5000 (runs, artifacts, Model Registry)

make promote APPROVER="Name"      # human gate: @champion <- @challenger (old champion -> @previous_champion)
make rollback REASON="why"        # @champion <- @previous_champion
make drift                        # PSI check of paths.drift_current_data
make drift-sim                    # same check on a simulated drifted snapshot

make reproduce             # wipe mlflow.db / mlartifacts / intermediate data, then re-run from scratch
make setup-airflow         # separate venv with apache-airflow==2.10.5 (official constraints)
make dag-check             # import both DAGs with real Airflow, list import errors
make airflow-test          # airflow dags test telco_churn_training
make airflow-test-drift SNAPSHOT=data/simulated/drifted_snapshot.csv
make docker-build docker-train    # same pipeline inside churnguard-train:1.1.0
```

Run one stage: `.venv/bin/python -m src.pipeline <stage>`; subset of experiments:
`.venv/bin/python -m src.pipeline train --only lr_baseline lr_eng_costthr`.

## Pipeline stages

| Stage | Input | Output | Quality gate |
|---|---|---|---|
| ingest | public IBM CSV URL | `data/raw/Telco-Customer-Churn.csv` + manifest | sha256 must equal `data.expected_sha256` (`DataIntegrityError`) |
| validate | raw CSV | `reports/validation_report.json` | 21 columns + dtypes, allowed categories, ranges, unique IDs, missing ≤ 1%, churn rate in [0.15, 0.40] (`DataValidationError`) |
| preprocess | raw CSV | `data/interim/{train,val,test}.csv` + `split_manifest.json` (rows, churn rate, sha256) | stratified split, seed 42 |
| features | interim splits | `data/processed/*.csv` + `feature_metadata.json` | finite numerics, no missing categoricals, `num_addon_services ∈ [0,6]` |
| train | processed splits | 16 MLflow runs (params, 41 metrics, plots, model, lineage tags) | 5-fold CV on train; threshold tuned on validation only |
| evaluate | MLflow runs of this execution | `reports/experiments.csv`, comparison charts | runs of exactly one `pipeline_run_id` |
| register | experiments table | registry version with alias `@challenger`, `gate_report.csv`, `challenger.json` | eligibility + 6 metric gates + beat `lr_baseline`, then simplicity rule; otherwise `QualityGateError` and the registry is untouched |

Stages communicate through files plus `reports/pipeline_state/<stage>.json`, so each stage is
idempotent and can be retried on its own (exactly what Airflow does on task failure).

## Experiment design

Variables: algorithm (LogReg, Random Forest, XGBoost, LightGBM), hyperparameters (defaults vs tuned,
RF capped at 300 trees), feature set (`base` = raw attributes, `engineered` = + tenure bucket, add-on
count, average spend, charge delta, month-to-month, auto-payment, family), imbalance handling (none,
class weights / `scale_pos_weight`, SMOTE inside the CV pipeline), decision threshold (0.5 vs
cost-optimal capped at the 20% contact capacity). Baseline: `lr_baseline` (LogReg, base features,
threshold 0.5). Two ablation runs (`*_gender_costthr`) add `gender` to measure what excluding it
costs; they are marked `eligible: false` and can never be registered.

**Selection metric:** expected business cost per customer on the validation split (lower is better),
tie-break PR-AUC. Test metrics are reported but never used for selection.

**Gates (validation split):** Recall@top-20% ≥ 0.48 (beats the A1 rule scorecard, 0.476),
ROC-AUC ≥ 0.83, PR-AUC ≥ 0.60, contact rate ≤ 0.20, gender recall gap (one-sided 95% lower
confidence bound) ≤ 0.05, Brier ≤ 0.17, and cost below `lr_baseline`. Among passing runs within
USD 0.15/customer of the best (≈ 0.005 Recall@top-20%), the simplest family wins.

### Business assumptions (not measured data — see `business:` in config, identical to A1)

| Assumption | Value | Derivation |
|---|---|---|
| churn_loss | USD 466.27 | 12 months × mean MonthlyCharges (USD 64.76) × 60% gross margin |
| offer_cost | USD 50 | retention incentive + agent contact per targeted customer |
| offer_success_rate | 25% | share of contacted true churners who stay |
| max_contact_rate / top_k_fraction | 20% | call-centre capacity per cycle |

cost(TP) = 50 + 0.75 × 466.27, cost(FP) = 50, cost(FN) = 466.27, cost(TN) = 0.
Break-even churn probability = 50 / (0.25 × 466.27) = 0.429.

## Results (pipeline execution `manual__2026-10-04T00:00:00+00:00`, from `reports/experiments.csv`)

| # | Run | Model | Features | Imbalance | Thr | Val cost/cust (USD) | Val R@20% | Val PR-AUC | Val ROC-AUC | Val contact | Val gender gap LCB | Val Brier | All gates | Test cost/cust (USD) | Test R@20% | Test ROC-AUC |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `lr_eng_costthr` | logistic_regression | engineered | none | 0.51 | 117.8287 | 0.5160 | 0.6499 | 0.8381 | 0.1973 | 0.0394 | 0.1374 | yes | 118.1951 | 0.5027 | 0.8458 |
| 2 | `lr_eng_gender_costthr` | logistic_regression | engineered_gender | none | 0.52 | 117.8402 | 0.5134 | 0.6494 | 0.8378 | 0.1909 | 0.0603 | 0.1375 | no | 118.1831 | 0.5053 | 0.8459 |
| 3 | `lr_baseline` | logistic_regression | base | none | 0.50 | 117.8885 | 0.5107 | 0.6434 | 0.8365 | 0.2150 | 0.0306 | 0.1380 | no | 117.8537 | 0.5027 | 0.8427 |
| 4 | `rf_tuned_eng_costthr` | random_forest | engineered | none | 0.50 | 118.2660 | 0.5027 | 0.6480 | 0.8391 | 0.1994 | 0.0712 | 0.1371 | no | 118.7272 | 0.4893 | 0.8418 |
| 5 | `rf_tuned_eng_gender_costthr` | random_forest | engineered_gender | none | 0.50 | 118.3841 | 0.4973 | 0.6444 | 0.8368 | 0.1952 | 0.0056 | 0.1380 | no | 118.5262 | 0.4947 | 0.8419 |
| 6 | `lgbm_smote_eng` | lightgbm | engineered | smote | 0.50 | 118.5756 | 0.4813 | 0.6285 | 0.8307 | 0.2520 | 0.0121 | 0.1445 | no | 118.1151 | 0.4920 | 0.8390 |
| 7 | `xgb_tuned_eng_costthr` | xgboost | engineered | none | 0.51 | 118.6322 | 0.4920 | 0.6372 | 0.8327 | 0.1952 | 0.0321 | 0.1406 | no | 118.2778 | 0.5053 | 0.8416 |
| 8 | `lgbm_eng_costthr` | lightgbm | engineered | none | 0.50 | 118.6915 | 0.4840 | 0.6372 | 0.8321 | 0.1980 | 0.0160 | 0.1414 | no | 118.4557 | 0.5027 | 0.8383 |
| 9 | `rf_default` | random_forest | base | none | 0.50 | 119.0938 | 0.4733 | 0.6047 | 0.8126 | 0.2094 | 0.0000 | 0.1489 | no | 119.1295 | 0.4706 | 0.8198 |
| 10 | `xgb_default_eng` | xgboost | engineered | none | 0.50 | 119.2237 | 0.4733 | 0.6057 | 0.8100 | 0.2087 | 0.0376 | 0.1543 | no | 119.1883 | 0.4733 | 0.8212 |
| 11 | `rf_tuned_balanced_eng` | random_forest | engineered | class_weight | 0.50 | 119.2314 | 0.5027 | 0.6459 | 0.8394 | 0.3875 | 0.0000 | 0.1580 | no | 119.0424 | 0.4973 | 0.8421 |
| 12 | `lgbm_balanced_eng` | lightgbm | engineered | class_weight | 0.50 | 119.6211 | 0.4947 | 0.6360 | 0.8331 | 0.3804 | 0.0000 | 0.1612 | no | 119.3846 | 0.4893 | 0.8389 |
| 13 | `lr_balanced_eng` | logistic_regression | engineered | class_weight | 0.50 | 119.7401 | 0.5080 | 0.6493 | 0.8385 | 0.4010 | 0.0066 | 0.1661 | no | 119.9297 | 0.5107 | 0.8462 |
| 14 | `lr_balanced` | logistic_regression | base | class_weight | 0.50 | 119.7996 | 0.5160 | 0.6426 | 0.8366 | 0.4088 | 0.0303 | 0.1678 | no | 120.0360 | 0.5027 | 0.8424 |
| 15 | `lr_smote_eng` | logistic_regression | engineered | smote | 0.50 | 119.8224 | 0.5080 | 0.6433 | 0.8381 | 0.3911 | 0.0000 | 0.1627 | no | 120.0003 | 0.5053 | 0.8451 |
| 16 | `xgb_tuned_spw_eng` | xgboost | engineered | class_weight | 0.50 | 120.1183 | 0.5000 | 0.6356 | 0.8350 | 0.4003 | 0.0000 | 0.1642 | no | 119.4092 | 0.5080 | 0.8420 |

Selected: **`lr_eng_costthr`** — the only run of 16 that passes every gate (see
`reports/gate_report.csv`). It was registered as `churnguard-classifier` v2 with alias
`@challenger`, then promoted to `@champion` by a (demo) human approval; v1 is `@previous_champion`.
Load with `mlflow.pyfunc.load_model("models:/churnguard-classifier@champion")`; the operating
threshold (0.51) is stored as a model-version tag. On test it reaches Recall@top-20% 0.5027,
ROC-AUC 0.8458, PR-AUC 0.6559 and saves USD 5,569.99 net per 1,000 customers versus no campaign
(under the assumptions above).

Observations: once regularised, all four families sit in a narrow validation ROC-AUC band
(0.83–0.84), so the decision policy moves cost more than the algorithm; class weights and SMOTE at
threshold 0.5 contact 25–41% of customers and break the capacity gate; untuned trees fail the
ranking gates; adding `gender` does not lower cost measurably. Open issues: test F1 0.5727 is
below the A1 minimum of 0.58, and the senior-citizen recall gap (0.2238 on validation) needs review.

## Reproducibility evidence

- Seed 42 everywhere (`set_global_seed`, split, CV, SMOTE, every estimator; LightGBM `deterministic=True`).
- Two independent executions — `make reproduce` (`local__20261003T191435Z`) and `make airflow-test`
  (`manual__2026-10-04T00:00:00+00:00`) — agree on all 39 compared metrics across the 16 runs
  (max absolute difference 2.78e-17), with identical thresholds and data hash
  (`reports/ops_evidence/reproducibility_check.json`).
- Inside Docker (`churnguard-train:1.1.0`, Linux) the full pipeline exits 0 and selects the same
  challenger (`lr_eng_costthr`, threshold 0.51, val cost 117.83); 8 of 16 runs are identical at log
  precision, tree/SMOTE runs differ slightly (largest PR-AUC difference 0.0042) because of
  platform-level floating-point and threading differences (`reports/ops_evidence/docker_train.log`).
  Bit-exact reproducibility is therefore guaranteed per environment, which is why the pinned image
  is the canonical training environment.
- Every run is tagged with `data_sha256`, `git_sha`, `git_dirty`, `seed`, `pipeline_run_id`, and logs
  `evaluation/experiment_config.json`; the model is logged with signature, input example and `src/`
  as `code_paths`.

## Airflow

Both DAGs were verified with real **Apache Airflow 2.10.5** (separate venv, official constraints;
see `reports/ops_evidence/airflow_evidence.txt`): no import errors; `telco_churn_training` ran all 7
tasks to `success` and registered the challenger; `telco_churn_drift_monitor` skipped downstream on
the current snapshot (max PSI 0.0017) and, on the simulated snapshot (max PSI 0.8416), emitted the
drift alert and queued a training run through the dataset.

- `telco_churn_training`: `DatasetOrTimeSchedule` — monthly cron `0 2 1 * *` (Asia/Ho_Chi_Minh)
  **or** the `churnguard://monitoring/drift-alert` dataset; `catchup=False`, `max_active_runs=1`,
  2 h DAG timeout.
- `telco_churn_drift_monitor`: weekly `0 1 * * 1`; `drift` → `ShortCircuitOperator` →
  `emit_drift_alert` (dataset outlet).
- Retries 2 with exponential back-off by default (ingest 3 for network errors, validate 0 since bad
  data is deterministic, train 1 with a 60 min timeout); `on_failure_callback` emits a structured
  `ALERT` log line and posts to `ALERT_WEBHOOK_URL` (https only) when set.
- Tasks run `python -m src.pipeline <stage>` with the project interpreter (`TELCO_PYTHON`), keeping
  Airflow's dependencies separate from the ML stack; the Airflow `run_id` becomes the
  `pipeline_run_id` tag that groups the MLflow runs of one DAG run.
- Promotion to `@champion` is deliberately not a DAG task: it needs `make promote APPROVER=...`.

## Docker

`make docker-build` builds `churnguard-train:1.1.0` from `python:3.12.11-slim-bookworm` (non-root
user, `libgomp1` for LightGBM/XGBoost, `xgboost-cpu` on Linux to avoid CUDA libraries) and bakes the
git commit into the image (`--build-arg GIT_SHA`) so containerised runs still carry a `git_sha` tag.
`make docker-train` runs `python -m src.pipeline all` with the MLflow backend in a named volume.

## Configuration

`configs/config.yaml` holds every default. Override any key with an environment variable:
`TELCO__<SECTION>__<KEY>=<yaml value>` (e.g. `TELCO__MLFLOW__TRACKING_URI=http://mlflow:5000`,
`TELCO__PROJECT__SEED=7`). `TELCO_CONFIG` selects another file. The Makefile loads `.env`
(see `.env.example`).

## Notes and limitations

- Data is the public IBM sample (7,043 customers, single snapshot), so "data versioning" is a
  sha256 pin plus per-split hashes; a production setup would version monthly CRM extracts (e.g. DVC).
  The drift DAG therefore compares the same file by default; `data/simulated/` exercises the alert path.
- Selection and threshold tuning both use the validation split, so validation cost is slightly
  optimistic for the `*_costthr` runs; the untouched test split is reported separately.
- The model is pickled (cloudpickle) because MLflow's default `skops` format rejects the custom
  transformer; artifacts are only loaded from our own registry.
