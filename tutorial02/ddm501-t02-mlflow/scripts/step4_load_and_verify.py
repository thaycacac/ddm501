"""
Step 4 — load it back, and prove it is the model you think it is.

Run:  python scripts/step4_load_and_verify.py
"""
import json

import mlflow
import numpy as np
import sklearn
import yaml
from mlflow import MlflowClient
from sklearn.datasets import load_breast_cancer
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split

from _common import MODEL_NAME, connect

ALIAS = "champion"


def main() -> None:
    connect()
    client = MlflowClient()

    # Production code names an alias, never a version number. This one line is
    # the entire interface between "who trained it" and "who serves it".
    uri = f"models:/{MODEL_NAME}@{ALIAS}"
    model = mlflow.sklearn.load_model(uri)
    print(f"loaded {uri}")

    # --- lineage: alias -> version -> run -> parameters ---------------------
    mv = client.get_model_version_by_alias(MODEL_NAME, ALIAS)
    run = client.get_run(mv.run_id)
    print(f"\n  version    {mv.version}")
    print(f"  run_id     {mv.run_id}")
    print(f"  run name   {run.data.tags.get('mlflow.runName')}")
    print(f"  params     {json.dumps(run.data.params, sort_keys=True)}")
    print(f"  logged cv  {float(run.data.metrics['cv_roc_auc_mean']):.5f} "
          f"+/- {float(run.data.metrics['cv_roc_auc_std']):.5f}")

    # --- the environment that pickled it ------------------------------------
    # Tutorial 01 asked "which scikit-learn version pickled this file?" and had
    # no way to find out. MLflow writes an MLmodel file next to every model.
    local = mlflow.artifacts.download_artifacts(f"{uri}")
    meta = yaml.safe_load(open(f"{local}/MLmodel"))
    flavour = meta["flavors"]["sklearn"]
    print(f"\n  pickled by sklearn {flavour['sklearn_version']}")
    print(f"  running   sklearn {sklearn.__version__}")
    if flavour["sklearn_version"] != sklearn.__version__:
        print("  MISMATCH. Loading may fail outright, not warn. See the note below.")
    else:
        print("  match -- safe to load")

    # --- does it still score what the run said it scored? -------------------
    X, y = load_breast_cancer(as_frame=True, return_X_y=True)
    _, X_te, _, y_te = train_test_split(
        X, y, test_size=0.2, stratify=y,
        random_state=int(run.data.params["split_seed"]))
    reproduced = roc_auc_score(y_te, model.predict_proba(X_te)[:, 1])
    logged = float(run.data.metrics["test_roc_auc"])
    print(f"\n  test_roc_auc logged at training time  {logged:.6f}")
    print(f"  test_roc_auc recomputed just now      {reproduced:.6f}")
    print("  identical" if np.isclose(logged, reproduced) else "  DIFFERENT -- investigate")


if __name__ == "__main__":
    main()
