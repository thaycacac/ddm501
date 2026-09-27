"""
BÀI 05 — bốn loại dữ liệu gắn vào một run (chưa đụng registry).

| Loại      | API                    | Ý nghĩa                         | Quy tắc ngắn              |
|-----------|------------------------|----------------------------------|---------------------------|
| Parameter | log_param / log_params | INPUT cấu hình                   | Ghi một lần, không sửa    |
| Metric    | log_metric / log_metrics | OUTPUT số đo                   | Có thể log nhiều lần      |
| Tag       | set_tag / set_tags     | Nhãn lọc / tìm trên UI           | Free-form string          |
| Artifact  | log_artifact           | FILE (plot, csv, model file…)    | Đính kèm run              |

Tutorial 02 step1 cũng log đủ bốn loại này — bài này thu nhỏ để nhìn rõ từng cái.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mlflow
import numpy as np
from sklearn.datasets import load_breast_cancer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import ConfusionMatrixDisplay, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from connect import connect

TMP = Path(__file__).resolve().parent / "_tmp"
TMP.mkdir(exist_ok=True)


def main() -> None:
    connect()

    X, y = load_breast_cancer(return_X_y=True)
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    C = 1.0
    model = make_pipeline(
        StandardScaler(),
        LogisticRegression(C=C, max_iter=5000, random_state=0),
    )

    with mlflow.start_run(run_name=f"logreg-C-{C}") as run:
        # --- PARAMETERS (inputs) -------------------------------------------
        mlflow.log_params(
            {
                "family": "logreg",
                "C": C,
                "split_seed": 42,
                "test_size": 0.2,
            }
        )

        model.fit(X_tr, y_tr)
        proba = model.predict_proba(X_te)[:, 1]
        pred = (proba >= 0.5).astype(int)
        auc = float(roc_auc_score(y_te, proba))

        # --- METRICS (outputs) ---------------------------------------------
        mlflow.log_metrics(
            {
                "test_roc_auc": auc,
                "n_test": float(len(y_te)),
            }
        )

        # --- TAGS (labels for search/filter) -------------------------------
        mlflow.set_tags({"dataset": "wdbc", "lesson": "05"})

        # --- ARTIFACTS (files kept with the run) ---------------------------
        fig, ax = plt.subplots(figsize=(3.2, 3.2))
        ConfusionMatrixDisplay.from_predictions(y_te, pred, ax=ax, colorbar=False)
        fig.tight_layout()
        png = TMP / "confusion_matrix.png"
        fig.savefig(png, dpi=110)
        plt.close(fig)
        mlflow.log_artifact(str(png))

        note = TMP / "notes.txt"
        note.write_text(
            f"run_id={run.info.run_id}\ntest_roc_auc={auc:.6f}\n",
            encoding="utf-8",
        )
        mlflow.log_artifact(str(note))

        print(f"run_id = {run.info.run_id}")
        print(f"test_roc_auc = {auc:.6f}")
        print("UI → experiment mlflow-course-05 → mở run → tabs Parameters / Metrics / Artifacts")


if __name__ == "__main__":
    main()
