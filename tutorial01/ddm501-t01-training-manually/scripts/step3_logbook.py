"""
Step 3 — the logbook you would have written yourself.

Run:  python scripts/step3_logbook.py --tag "rf only"
"""
import argparse
import csv
import datetime as dt
import platform
from pathlib import Path

import joblib
import numpy as np
import sklearn
from sklearn.datasets import load_breast_cancer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "logs" / "results.csv"
FIELDS = ["timestamp", "tag", "n_estimators", "max_depth", "seed",
          "roc_auc", "recall_malignant", "sklearn", "python"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="untitled")
    ap.add_argument("--n-estimators", type=int, default=200)
    ap.add_argument("--max-depth", type=int, default=None)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    X, y = load_breast_cancer(as_frame=True, return_X_y=True)
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=args.seed)

    model = make_pipeline(StandardScaler(), RandomForestClassifier(
        n_estimators=args.n_estimators, max_depth=args.max_depth,
        random_state=args.seed))
    model.fit(X_tr, y_tr)

    proba = model.predict_proba(X_te)[:, 1]
    row = {
        "timestamp": dt.datetime.now().isoformat(timespec="seconds"),
        "tag": args.tag,
        "n_estimators": args.n_estimators,
        "max_depth": args.max_depth,
        "seed": args.seed,
        "roc_auc": round(float(roc_auc_score(y_te, proba)), 5),
        "recall_malignant": round(float(recall_score(
            y_te, (proba >= 0.5).astype(int), pos_label=0)), 5),
        "sklearn": sklearn.__version__,
        "python": platform.python_version(),
    }

    LOG.parent.mkdir(exist_ok=True)
    new = not LOG.exists()
    with LOG.open("a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow(row)

    joblib.dump(model, ROOT / "models" / f"model_{args.tag.replace(' ', '_')}.joblib")
    print(f"logged -> logs/results.csv   ({sum(1 for _ in LOG.open()) - 1} runs so far)")
    for k, v in row.items():
        print(f"  {k:18s} {v}")

    print("""
This is already a real improvement, and it is roughly what every team builds
before they adopt a tracking tool. Run it four or five times with different
--tag and --n-estimators, then look at logs/results.csv and ask:

  1. The CSV has a column per hyper-parameter. You now want to try an SVM
     with a `gamma`. Where does that column go, and what do the older rows
     contain for it?
  2. Which row produced models/model_untitled.joblib? What if you ran the
     same tag twice?
  3. You want to keep the confusion matrix and the ROC curve for each run.
     Where do they live?
  4. Two people run this at once. Open the CSV and look at the last lines.
  5. Six months from now, which commit of this repository produced row 3?

""")


if __name__ == "__main__":
    main()
