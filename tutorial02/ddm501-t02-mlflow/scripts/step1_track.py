"""
Step 1 — the same search as Tutorial 01, this time recorded.

Nothing about the modelling changes. What changes is that every configuration
becomes a run with parameters, metrics, tags and files attached to it.

Run:  python scripts/step1_track.py
"""
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")                      # no display in a terminal
import matplotlib.pyplot as plt
import mlflow
import numpy as np
import sklearn
from sklearn.datasets import load_breast_cancer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (ConfusionMatrixDisplay, recall_score,
                             roc_auc_score)
from sklearn.model_selection import (RepeatedStratifiedKFold, cross_val_score,
                                     train_test_split)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from _common import connect

warnings.filterwarnings("ignore")
TMP = Path(__file__).resolve().parents[1] / "artifacts"

# Twelve configurations, three families. Small enough to finish in a couple of
# minutes, large enough that reading the results off a terminal stops working.
CONFIGS = [
    ("rf",     {"n_estimators": n, "max_depth": d})
    for n in (100, 400) for d in (3, 8, None)
] + [
    ("svc",    {"C": c, "gamma": g}) for c in (1.0, 10.0) for g in ("scale", 0.01)
] + [
    ("logreg", {"C": c}) for c in (0.1, 1.0)
]


def build(family: str, params: dict):
    clf = {"rf": RandomForestClassifier, "svc": SVC,
           "logreg": LogisticRegression}[family]
    kwargs = dict(params, random_state=0)
    if family == "svc":
        kwargs.update(probability=True, max_iter=200_000)
    if family == "logreg":
        kwargs.update(max_iter=5000)
    return make_pipeline(StandardScaler(), clf(**kwargs))


def main() -> None:
    connect()
    TMP.mkdir(exist_ok=True)

    X, y = load_breast_cancer(as_frame=True, return_X_y=True)
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42)
    cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=3, random_state=0)

    for family, params in CONFIGS:
        model = build(family, params)

        # Everything between start_run() and the end of the block belongs to
        # one run. Crash halfway and the run is still there, marked FAILED,
        # with whatever you had logged so far.
        with mlflow.start_run(run_name=f"{family}-{'-'.join(map(str, params.values()))}"):
            scores = cross_val_score(model, X_tr, y_tr, cv=cv, scoring="roc_auc",
                                     n_jobs=-1)
            model.fit(X_tr, y_tr)
            proba = model.predict_proba(X_te)[:, 1]
            pred = (proba >= 0.5).astype(int)

            # PARAMETERS: inputs. Strings, written once, never updated.
            mlflow.log_params({"family": family, **params})
            mlflow.log_param("cv", "RepeatedStratifiedKFold(5x3, seed=0)")
            mlflow.log_param("split_seed", 42)

            # METRICS: outputs. Numbers, and you can log more than the headline.
            # cv_std is the column Tutorial 01 could not add to its CSV, and it
            # is the one that decides whether a ranking means anything.
            mlflow.log_metrics({
                "cv_roc_auc_mean": float(np.mean(scores)),
                "cv_roc_auc_std": float(np.std(scores)),
                "test_roc_auc": float(roc_auc_score(y_te, proba)),
                "test_recall_malignant": float(recall_score(y_te, pred, pos_label=0)),
            })

            # TAGS: free-form labels you search by later.
            mlflow.set_tags({"dataset": "wdbc-569", "sklearn": sklearn.__version__})

            # ARTIFACTS: files. Anything you would otherwise lose.
            fig, ax = plt.subplots(figsize=(3.2, 3.2))
            ConfusionMatrixDisplay.from_predictions(
                y_te, pred, display_labels=["malignant", "benign"],
                colorbar=False, ax=ax)
            fig.tight_layout()
            png = TMP / "confusion_matrix.png"
            fig.savefig(png, dpi=110)
            plt.close(fig)
            mlflow.log_artifact(png)

            # THE MODEL ITSELF, with its flavour metadata: the library and the
            # version that pickled it travel with the file.
            mlflow.sklearn.log_model(model, artifact_path="model",
                                     input_example=X_te.head(2))

            print(f"  logged {family:6s} {str(params):38s} "
                  f"cv {np.mean(scores):.5f} +/- {np.std(scores):.5f}")

    print(f"\n{len(CONFIGS)} runs logged. Open http://127.0.0.1:5000 and look at them.")


if __name__ == "__main__":
    main()
