"""
Step 2 — answering the questions Tutorial 01 could not.

Everything here reads the tracking server. No model is trained. This is the
step where the record-keeping starts paying for itself.

Run:  python scripts/step2_compare.py
"""
import mlflow
import pandas as pd

from _common import EXPERIMENT, connect

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 40)


def main() -> None:
    connect()
    runs = mlflow.search_runs(experiment_names=[EXPERIMENT],
                              order_by=["metrics.cv_roc_auc_mean DESC"])
    print(f"{len(runs)} runs on the server.\n")

    cols = {"tags.mlflow.runName": "run",
            "params.family": "family",
            "metrics.cv_roc_auc_mean": "cv_mean",
            "metrics.cv_roc_auc_std": "cv_std",
            "metrics.test_recall_malignant": "recall_mal"}
    table = runs[list(cols)].rename(columns=cols)
    print(table.head(12).to_string(index=False,
          formatters={"cv_mean": "{:.5f}".format, "cv_std": "{:.5f}".format,
                      "recall_mal": "{:.4f}".format}))

    best = runs.iloc[0]
    print(f"\nBest by cv_roc_auc_mean : {best['tags.mlflow.runName']}")
    print(f"  run_id                : {best['run_id']}")
    print(f"  cv                    : {best['metrics.cv_roc_auc_mean']:.5f} "
          f"+/- {best['metrics.cv_roc_auc_std']:.5f}")

    # Tutorial 01, question 2: "which run had the best recall?" -- a different
    # question from "which had the best AUC", and one sort away instead of
    # a re-run away.
    by_recall = runs.sort_values("metrics.test_recall_malignant", ascending=False).iloc[0]
    print(f"\nBest by recall on malignant : {by_recall['tags.mlflow.runName']}"
          f"  ({by_recall['metrics.test_recall_malignant']:.4f})")
    if by_recall["run_id"] != best["run_id"]:
        print("  -> a DIFFERENT run than the AUC winner. On this dataset the two")
        print("     metrics disagree, and only one of them matches what a missed")
        print("     cancer costs.")

    # And the question that decides whether any of this ranking is meaningful.
    top = runs.head(10)
    gap = top["metrics.cv_roc_auc_mean"].iloc[0] - top["metrics.cv_roc_auc_mean"].iloc[-1]
    std = top["metrics.cv_roc_auc_std"].iloc[0]
    print(f"\ngap over the 10th run   {gap:.5f}")
    print(f"std of the winner       {std:.5f}")
    print("  -> the ranking is inside the noise" if gap < std else
          "  -> the ranking is outside the noise")

    # Where the signal actually is. Comparing across families and comparing
    # inside one family are two different questions, and only one of them has
    # an answer at this sample size.
    print("\nwithin each family, best minus worst, against the family's own spread:")
    for fam, grp in runs.groupby("params.family"):
        spread = (grp["metrics.cv_roc_auc_mean"].max()
                  - grp["metrics.cv_roc_auc_mean"].min())
        std = grp["metrics.cv_roc_auc_std"].mean()
        verdict = "noise" if spread < std else "real"
        print(f"  {fam:7s} n={len(grp):2d}  spread {spread:.5f}  mean std {std:.5f}  -> {verdict}")
    print("  The choice of family is a real effect here. The hyper-parameter")
    print("  tuning inside each family is not. Those are different claims and")
    print("  they need different evidence.")

    print("""
--------------------------------------------------------------------------
Now open http://127.0.0.1:5000 and do it with your eyes instead:

  1. Select all runs, press Compare, and open the Parallel Coordinates tab.
     Drag cv_roc_auc_mean. Which hyper-parameter actually moves the score?
  2. Sort by test_recall_malignant instead. Does the order change?
  3. Open any run, then the Artifacts tab. The confusion matrix is there,
     attached to the run that produced it.
  4. Add the cv_roc_auc_std column to the table view. Ten runs, one column,
     no CSV surgery.

Tutorial 01 asked for all four of these and could not deliver any of them.
--------------------------------------------------------------------------""")


if __name__ == "__main__":
    main()
