"""
BÀI 10 — Load bằng alias + lineage + chứng minh đúng model (T02 step4).

Interface production chỉ cần một URI:
  models:/lesson-09-classifier@champion

Chuỗi truy vết:
  alias → version → run_id → params/metrics → MLmodel (sklearn_version)

Rồi: load model → predict trên cùng split_seed → so với metric đã log (nếu có).
Bài 09 không log test_roc_auc; bài này log metric rồi verify luôn cho đủ vòng.
"""
from __future__ import annotations

import json
import os

import mlflow
import numpy as np
import sklearn
import yaml
from mlflow import MlflowClient
from sklearn.datasets import load_breast_cancer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5001")
EXPERIMENT = "mlflow-course-10"
MODEL_NAME = "lesson-10-classifier"
ALIAS = "champion"
SPLIT_SEED = 42


def seed_champion() -> None:
    """Một lần: train → log metric → register → alias champion."""
    mlflow.set_experiment(EXPERIMENT)
    X, y = load_breast_cancer(as_frame=True, return_X_y=True)
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=SPLIT_SEED
    )
    model = make_pipeline(
        StandardScaler(),
        LogisticRegression(C=1.0, max_iter=5000, random_state=0),
    )
    model.fit(X_tr, y_tr)
    auc = float(roc_auc_score(y_te, model.predict_proba(X_te)[:, 1]))

    with mlflow.start_run(run_name="seed-for-load") as run:
        mlflow.log_params({"C": 1.0, "split_seed": SPLIT_SEED})
        mlflow.log_metric("test_roc_auc", auc)
        mlflow.sklearn.log_model(model, "model", input_example=X_te.head(2))
        run_id = run.info.run_id

    mv = mlflow.register_model(f"runs:/{run_id}/model", MODEL_NAME)
    MlflowClient().set_registered_model_alias(MODEL_NAME, ALIAS, str(mv.version))
    print(f"seeded {MODEL_NAME}@{ALIAS} version={mv.version} test_roc_auc={auc:.6f}")


def verify() -> None:
    uri = f"models:/{MODEL_NAME}@{ALIAS}"
    model = mlflow.sklearn.load_model(uri)
    print(f"loaded {uri}")

    client = MlflowClient()
    mv = client.get_model_version_by_alias(MODEL_NAME, ALIAS)
    run = client.get_run(mv.run_id)
    print(f"\n  version   {mv.version}")
    print(f"  run_id    {mv.run_id}")
    print(f"  run name  {run.data.tags.get('mlflow.runName')}")
    print(f"  params    {json.dumps(run.data.params, sort_keys=True)}")
    logged = float(run.data.metrics["test_roc_auc"])
    print(f"  logged test_roc_auc {logged:.6f}")

    local = mlflow.artifacts.download_artifacts(uri)
    meta = yaml.safe_load(open(f"{local}/MLmodel"))
    pickled = meta["flavors"]["sklearn"]["sklearn_version"]
    print(f"\n  pickled sklearn {pickled}")
    print(f"  running sklearn {sklearn.__version__}")
    print("  match" if pickled == sklearn.__version__ else "  MISMATCH")

    X, y = load_breast_cancer(as_frame=True, return_X_y=True)
    _, X_te, _, y_te = train_test_split(
        X, y, test_size=0.2, stratify=y,
        random_state=int(run.data.params["split_seed"]),
    )
    reproduced = float(roc_auc_score(y_te, model.predict_proba(X_te)[:, 1]))
    print(f"\n  recomputed test_roc_auc {reproduced:.6f}")
    print("  identical" if np.isclose(logged, reproduced) else "  DIFFERENT")


def main() -> None:
    mlflow.set_tracking_uri(TRACKING_URI)
    # Luôn seed version mới + trỏ champion vào nó (idempotent cho lab).
    seed_champion()
    print("---")
    verify()


if __name__ == "__main__":
    main()
