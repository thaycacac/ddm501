"""
Step 1 — one model, one number.

Trains a single random forest on the Wisconsin Diagnostic Breast Cancer data
and prints the usual metrics.

Run:  python scripts/step1_baseline.py
"""
from pathlib import Path

import joblib
from sklearn.datasets import load_breast_cancer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (accuracy_score, confusion_matrix, recall_score,
                             roc_auc_score)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

MODELS = Path(__file__).resolve().parents[1] / "models"


def main() -> None:
    data = load_breast_cancer(as_frame=True)
    X, y = data.data, data.target

    # In this dataset 0 = malignant and 1 = benign.
    print(f"rows={len(X)}  features={X.shape[1]}  "
          f"malignant={int((y == 0).sum())}  benign={int((y == 1).sum())}")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    model = make_pipeline(
        StandardScaler(),
        RandomForestClassifier(n_estimators=200, random_state=42),
    )
    model.fit(X_train, y_train)

    proba = model.predict_proba(X_test)[:, 1]
    pred = (proba >= 0.5).astype(int)

    print(f"\naccuracy          {accuracy_score(y_test, pred):.4f}")
    print(f"roc_auc           {roc_auc_score(y_test, proba):.4f}")
    print(f"recall(malignant) {recall_score(y_test, pred, pos_label=0):.4f}")
    tn, fp, fn, tp = confusion_matrix(y_test, pred).ravel()
    print(f"\nconfusion matrix (rows = truth)")
    print(f"  malignant:  caught {tn:3d}   missed {fp:3d}   <- these are the costly ones")
    print(f"  benign:     flagged {fn:3d}   cleared {tp:3d}")

    MODELS.mkdir(exist_ok=True)
    joblib.dump(model, MODELS / "model.joblib")
    print(f"\nsaved -> models/model.joblib")

    print("""
Before you move on, write down the answers. We will need them in step 4 and you will not be able to recover them from anything on disk:
  1. What was the test ROC AUC, to four decimals?
  2. What random_state produced it?
  3. How many trees?
  4. Which scikit-learn version pickled models/model.joblib?
  5. Was the data scaled?
""")

if __name__ == "__main__":
    main()