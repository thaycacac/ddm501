"""Feasibility check used to set realistic model targets in Assignment 1.

Runs 5-fold stratified cross-validation of two untuned candidates on the IBM Telco data
and writes ``report/data/feasibility.json``. This is a sizing check only; the real
experiments, hold-out evaluation and model selection belong to Assignment 2.

Usage:
    python report/scripts/feasibility_check.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

REPORT_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = REPORT_DIR / "data" / "Telco-Customer-Churn.csv"
OUT_PATH = REPORT_DIR / "data" / "feasibility.json"
SEED = 42
NUMERIC = ["tenure", "MonthlyCharges", "TotalCharges"]


def main() -> None:
    df = pd.read_csv(DATA_PATH)
    df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce").fillna(0.0)
    y = (df["Churn"] == "Yes").astype(int).to_numpy()
    X = df.drop(columns=["customerID", "Churn", "gender"])
    categorical = [c for c in X.columns if c not in NUMERIC]
    pre = ColumnTransformer(
        [("num", StandardScaler(), NUMERIC), ("cat", OneHotEncoder(handle_unknown="ignore"), categorical)]
    )
    candidates = {
        "logistic_regression": LogisticRegression(max_iter=2000),
        "hist_gradient_boosting": HistGradientBoostingClassifier(
            max_depth=3, learning_rate=0.05, max_iter=300, random_state=SEED
        ),
    }
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    k = int(round(0.2 * len(y)))
    results = {}
    for name, model in candidates.items():
        proba = cross_val_predict(make_pipeline(pre, model), X, y, cv=cv, method="predict_proba")[:, 1]
        top = np.argsort(-proba)[:k]
        results[name] = {
            "roc_auc": round(float(roc_auc_score(y, proba)), 4),
            "pr_auc": round(float(average_precision_score(y, proba)), 4),
            "recall_at_top20": round(float(y[top].sum() / y.sum()), 4),
        }
    out = {"protocol": "5-fold stratified CV, out-of-fold predictions, gender excluded, seed 42", "results": results}
    OUT_PATH.write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
