"""
Step 2 — 30 models, one number each.

Run:  python scripts/step2_random_search.py
      python scripts/step2_random_search.py --seed 7
      python scripts/step2_random_search.py --no-scaling
"""
import argparse
import os
import warnings
from pathlib import Path

import joblib
import numpy as np
from sklearn.datasets import load_breast_cancer
from sklearn.exceptions import ConvergenceWarning
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import RandomizedSearchCV, StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler
from sklearn.svm import SVC

MODELS = Path(__file__).resolve().parents[1] / "models"
N_ITER = 30

# RandomizedSearchCV accepts a LIST of grids and samples across all of them,
# which is how one search covers three model families.
GRIDS = [
    {"clf": [RandomForestClassifier(random_state=0)],
     "clf__n_estimators": [50, 100, 200, 400],
     "clf__max_depth": [3, 5, 8, None],
     "clf__min_samples_leaf": [1, 2, 4, 8]},
    # max_iter is capped so the --no-scaling run terminates. An RBF SVM on
    # unscaled features where one column ranges 0-0.2 and another 0-4000 may
    # never converge; without a cap the script simply appears to hang.
    {"clf": [SVC(probability=True, random_state=0, max_iter=200_000)],
     "clf__C": [0.1, 1.0, 10.0, 100.0],
     "clf__gamma": ["scale", "auto", 0.01, 0.001],
     "clf__kernel": ["rbf", "poly"]},
    {"clf": [LogisticRegression(max_iter=5000, random_state=0)],
     "clf__C": [0.01, 0.1, 1.0, 10.0],
     "clf__penalty": ["l2"]},
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--no-scaling", action="store_true")
    args = ap.parse_args()

    data = load_breast_cancer(as_frame=True)
    X, y = data.data, data.target

    if args.no_scaling:
        # One column of this dataset ranges 0-0.2 and another 0-4000. Feed that
        # to an RBF SVM and the solver hits its iteration cap on almost every
        # fit.
        warnings.filterwarnings("ignore", category=ConvergenceWarning)
        # n_jobs=-1 fits in separate processes and a filter set here does not
        # reach them;
        os.environ["PYTHONWARNINGS"] = "ignore"
        print("NOTE: running WITHOUT scaling. The SVM solver will not converge;\n"
              "      compare the scores below against the scaled run.\n")

    scaler = FunctionTransformer() if args.no_scaling else StandardScaler()
    pipe = Pipeline([("scale", scaler), ("clf", RandomForestClassifier())])

    search = RandomizedSearchCV(
        pipe, GRIDS, n_iter=N_ITER, scoring="roc_auc",
        cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=args.seed),
        random_state=args.seed, n_jobs=-1,
    )
    search.fit(X, y)

    order = np.argsort(-search.cv_results_["mean_test_score"])[:5]
    print(f"{N_ITER} configurations tried. Top 5 by mean roc_auc:\n")
    for rank, i in enumerate(order, 1):
        name = type(search.cv_results_["param_clf"][i]).__name__
        print(f"  {rank}. {search.cv_results_['mean_test_score'][i]:.5f}  {name}")

    MODELS.mkdir(exist_ok=True)
    joblib.dump(search.best_estimator_, MODELS / "model.joblib")
    print(f"\nbest mean roc_auc {search.best_score_:.5f}")
    print("saved -> models/model.joblib")

    print("""
Run this script two more times:

    python scripts/step2_random_search.py --seed 7
    python scripts/step2_random_search.py --no-scaling

Then answer:

  a. Which of the three runs produced the models/model.joblib you have now?
  b. Which run had the best recall on malignant cases?
  c. Run 2 tried 30 configurations. What were the other 29?
  d. Reproduce the 17th configuration of run 2.
  e. Two teammates run this at the same time on a shared machine. What
     happens to models/model.joblib?

You cannot answer any of them, and nothing you did was careless. The
information was never written down anywhere.
""")


if __name__ == "__main__":
    main()
