"""
BÀI 07 — search_runs: đọc lại server, xếp hạng, không train lại.

Đây là tinh thần Tutorial 02 step2_compare.py:
  tracking trả lời câu hỏi bằng query — không phải mở CSV / chạy lại experiment.
"""
from __future__ import annotations

import os

import mlflow
import pandas as pd

TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5001")
EXPERIMENT = "mlflow-course-07"

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 40)


def main() -> None:
    mlflow.set_tracking_uri(TRACKING_URI)

    # order_by: metric cao → thấp (giống sort trên UI)
    runs = mlflow.search_runs(
        experiment_names=[EXPERIMENT],
        order_by=["metrics.cv_roc_auc_mean DESC"],
    )
    print(f"{len(runs)} runs on server\n")

    cols = {
        "tags.mlflow.runName": "run",
        "params.family": "family",
        "metrics.cv_roc_auc_mean": "cv_mean",
        "metrics.cv_roc_auc_std": "cv_std",
        "metrics.test_roc_auc": "test_auc",
    }
    table = runs[list(cols)].rename(columns=cols)
    print(table.to_string(index=False))

    best = runs.iloc[0]
    print(f"\nBest by cv_roc_auc_mean: {best['tags.mlflow.runName']}")
    print(f"  run_id = {best['run_id']}")

    # Đổi metric xếp hạng — một sort, không train lại (bài học T01/T02).
    by_test = runs.sort_values("metrics.test_roc_auc", ascending=False).iloc[0]
    print(f"Best by test_roc_auc:    {by_test['tags.mlflow.runName']}")
    if by_test["run_id"] != best["run_id"]:
        print("  → khác winner CV — metric khác có thể chọn model khác")


if __name__ == "__main__":
    main()
