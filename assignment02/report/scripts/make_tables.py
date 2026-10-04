"""Generate every results table of A2_report.md from the pipeline's exported files.

Tables are written between ``<!-- BEGIN:name -->`` / ``<!-- END:name -->`` markers
in the report, so the numbers in the PDF are always the numbers MLflow exported.

Sources (all produced by ``make train`` / ``make airflow-test`` in ``code/``):
    reports/experiments.csv     one row per MLflow run (export of mlflow.search_runs)
    reports/gate_report.csv     gate outcome per run (src.register.gate_report)
    reports/pipeline_state/preprocess.json   split sizes and hashes
    reports/ops_evidence/docker_train.log    same pipeline inside the Docker image

Usage:
    python report/scripts/make_tables.py            # rewrite tables in place
    python report/scripts/make_tables.py --check    # exit 1 if any table is stale
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import pandas as pd
import yaml

REPORT_DIR = Path(__file__).resolve().parents[1]
CODE_DIR = REPORT_DIR.parent / "code"
REPORT_MD = REPORT_DIR / "A2_report.md"

# A1 model goals (Assignment 1, Section 3.4): (minimum acceptable, target, direction).
A1_GOALS = {
    "recall_at_top_k": ("Recall@top-20%", 0.48, 0.50, "min"),
    "precision_at_top_k": ("Precision@top-20%", 0.60, 0.66, "min"),
    "roc_auc": ("ROC-AUC", 0.83, 0.84, "min"),
    "pr_auc": ("PR-AUC", 0.60, 0.64, "min"),
    "f1": ("F1 at operating threshold", 0.58, 0.62, "min"),
    "brier": ("Brier score", 0.17, 0.15, "max"),
    "gender_recall_gap": ("Gender recall gap (point)", 0.05, 0.05, "max"),
}

GATE_LABELS = {
    "eligible": "ineligible",
    "val_recall_at_top_k>=0.48": "R@20",
    "val_roc_auc>=0.83": "ROC",
    "val_pr_auc>=0.6": "PR",
    "val_contact_rate<=0.2": "capacity",
    "val_gender_recall_gap_lcb<=0.05": "fairness",
    "val_brier<=0.17": "Brier",
    "beats_baseline": "baseline",
}

PARAM_SHORT = {
    "C": "C",
    "n_estimators": "trees",
    "max_depth": "depth",
    "min_samples_leaf": "leaf",
    "max_features": "feat",
    "learning_rate": "lr",
    "subsample": "sub",
    "colsample_bytree": "col",
    "min_child_weight": "mcw",
    "num_leaves": "leaves",
    "min_child_samples": "mcs",
}
MODEL_SHORT = {
    "logistic_regression": "LogReg",
    "random_forest": "RandomForest",
    "xgboost": "XGBoost",
    "lightgbm": "LightGBM",
}


def f4(value: float) -> str:
    return f"{value:.4f}"


def md_table(header: list[str], rows: list[list[str]], align: str | None = None) -> str:
    align = align or "l" * len(header)
    sep = ["---:" if a == "r" else ":---:" if a == "c" else "---" for a in align]
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join(sep) + "|"]
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(lines)


def load() -> dict:
    runs = pd.read_csv(CODE_DIR / "reports" / "experiments.csv")
    gates = pd.read_csv(CODE_DIR / "reports" / "gate_report.csv")
    config = yaml.safe_load((CODE_DIR / "configs" / "config.yaml").read_text())
    splits = json.loads((CODE_DIR / "reports" / "pipeline_state" / "preprocess.json").read_text())
    docker = {}
    for line in (CODE_DIR / "reports" / "ops_evidence" / "docker_train.log").read_text().splitlines():
        m = re.search(r"src\.train (\S+)\s+val_pr_auc=([\d.]+) val_cost=([\d.]+) thr=([\d.]+)", line)
        if m:
            docker[m[1]] = (float(m[2]), float(m[3]), float(m[4]))
    assert runs["pipeline_run_id"].nunique() == 1, "experiments.csv must hold one pipeline run"
    return {"runs": runs, "gates": gates, "config": config, "splits": splits, "docker": docker}


def failed_gates(gates: pd.DataFrame, run_name: str) -> str:
    row = gates[gates["run_name"] == run_name].iloc[0]
    if bool(row["passed"]):
        return "**all passed**"
    failed = [label for col, label in GATE_LABELS.items() if not bool(row[col])]
    return ", ".join(failed)


def table_matrix(d: dict) -> str:
    runs = d["runs"].set_index("run_name")
    baseline = d["config"]["selection"]["baseline_experiment"]
    rows = []
    for i, exp in enumerate(d["config"]["experiments"], start=1):
        r = runs.loc[exp["name"]]
        params = []
        for key, short in PARAM_SHORT.items():
            value = r.get(f"model__{key}")
            if pd.notna(value):
                value = int(value) if isinstance(value, float) and value.is_integer() else value
                params.append(f"{short}={value}")
        if exp["name"] == baseline:
            role = "Baseline"
        elif str(r["eligible"]).lower() == "false":
            role = "Ablation"
        else:
            role = "Candidate"
        thr = "fixed 0.50" if r["threshold_strategy"] == "fixed" else "cost-opt."
        rows.append(
            [
                f"E{i:02d}",
                f"`{exp['name']}`",
                MODEL_SHORT[r["model"]],
                r["feature_set"].replace("engineered_gender", "eng.+gender"),
                r["imbalance"].replace("class_weight", "class wt."),
                thr,
                ", ".join(params),
                role,
            ]
        )
    return md_table(
        ["ID", "Run name", "Algorithm", "Features", "Imbalance", "Threshold", "Hyperparameters", "Role"],
        rows,
    )


def table_results_val(d: dict) -> str:
    rows = []
    for rank, r in enumerate(d["runs"].itertuples(), start=1):
        rows.append(
            [
                str(rank),
                f"`{r.run_name}`",
                f"{r.threshold:.2f}",
                f4(r.val_business_cost_per_customer),
                f4(r.val_recall_at_top_k),
                f4(r.val_precision_at_top_k),
                f4(r.val_pr_auc),
                f4(r.val_roc_auc),
                f4(r.val_f1),
                f4(r.val_contact_rate),
                f4(r.val_brier),
                f4(r.val_gender_recall_gap_lcb),
                failed_gates(d["gates"], r.run_name),
            ]
        )
    return md_table(
        ["#", "Run", "Thr.", "Cost/cust. (USD)", "R@20", "P@20", "PR-AUC", "ROC-AUC", "F1",
         "Contact", "Brier", "Gap LCB", "Failed gates"],
        rows,
        "rlrrrrrrrrrrl",
    )


def table_results_test(d: dict) -> str:
    rows = []
    for r in d["runs"].itertuples():
        rows.append(
            [
                f"`{r.run_name}`",
                f4(r.test_business_cost_per_customer),
                f4(r.test_recall_at_top_k),
                f4(r.test_precision_at_top_k),
                f4(r.test_pr_auc),
                f4(r.test_roc_auc),
                f4(r.test_f1),
                f4(r.test_contact_rate),
                f4(r.test_brier),
                f4(r.test_gender_recall_gap),
                f"{r.cv_roc_auc_mean:.4f} ± {r.cv_roc_auc_std:.4f}",
                f"{r.inference_ms_per_1k_rows:.2f}",
            ]
        )
    return md_table(
        ["Run", "Cost/cust. (USD)", "R@20", "P@20", "PR-AUC", "ROC-AUC", "F1", "Contact",
         "Brier", "Gender gap", "CV ROC-AUC", "ms/1k"],
        rows,
        "lrrrrrrrrrrr",
    )


def table_champion(d: dict) -> str:
    r = d["runs"].iloc[0]
    rows = []
    for key, (label, minimum, target, direction) in A1_GOALS.items():
        val, test = float(r[f"val_{key}"]), float(r[f"test_{key}"])
        if direction == "min":
            status = "meets target" if test >= target else "meets minimum" if test >= minimum else "**below minimum**"
            bound = f"≥ {minimum:.2f} / ≥ {target:.2f}"
        else:
            status = "meets target" if test <= target else "meets minimum" if test <= minimum else "**above maximum**"
            bound = f"≤ {minimum:.2f} / ≤ {target:.2f}"
        if key == "gender_recall_gap":
            bound = "≤ 0.05"
            status += f"; val gated on LCB {f4(float(r['val_gender_recall_gap_lcb']))}"
        rows.append([label, bound, f4(val), f4(test), status])
    gap_val, gap_test = float(r["val_senior_recall_gap"]), float(r["test_senior_recall_gap"])
    rows.append(
        ["Senior recall gap (monitor)", "review if > 0.15", f4(gap_val), f4(gap_test),
         "**review flagged (val)**" if max(gap_val, gap_test) > 0.15 else "ok"]
    )
    rows.append(
        ["CV ROC-AUC std (5-fold)", "< 0.02", f4(float(r["cv_roc_auc_std"])), "n/a",
         "ok" if r["cv_roc_auc_std"] < 0.02 else "**too unstable**"]
    )
    return md_table(["Metric (A1 Section 3.4)", "A1 min / target", "Validation", "Test", "Status (test)"], rows, "llrrl")


def table_ablation(d: dict) -> str:
    runs = d["runs"].set_index("run_name")
    rows = []
    pairs = (("LogReg", "lr_eng_costthr", "lr_eng_gender_costthr"),
             ("RandomForest", "rf_tuned_eng_costthr", "rf_tuned_eng_gender_costthr"))
    for family, without, with_g in pairs:
        a, b = runs.loc[without], runs.loc[with_g]
        for metric, label in (
            ("val_business_cost_per_customer", "Val cost/cust. (USD)"),
            ("val_pr_auc", "Val PR-AUC"),
            ("val_recall_at_top_k", "Val R@20"),
            ("test_business_cost_per_customer", "Test cost/cust. (USD)"),
            ("test_pr_auc", "Test PR-AUC"),
        ):
            rows.append([family, label, f4(a[metric]), f4(b[metric]), f"{b[metric] - a[metric]:+.4f}"])
    return md_table(["Family", "Metric", "Without gender", "With gender", "Δ (with − without)"], rows, "llrrr")


def table_splits(d: dict) -> str:
    rows = []
    for name in ("train", "val", "test"):
        s = d["splits"][name]
        rows.append([name, f"{s['rows']:,}", f"{s['churn_rate']:.4f}", f"`{s['sha256'][:16]}…`"])
    return md_table(["Split", "Rows", "Churn rate", "SHA-256 (prefix)"], rows, "lrrl")


def table_docker(d: dict) -> str:
    rows = []
    for r in d["runs"].itertuples():
        pr, cost, thr = d["docker"][r.run_name]
        same = (round(r.val_pr_auc, 4), round(r.val_business_cost_per_customer, 2), r.threshold) == (pr, cost, thr)
        if same:
            continue
        rows.append(
            [f"`{r.run_name}`", f"{r.val_business_cost_per_customer:.2f}", f"{cost:.2f}",
             f4(r.val_pr_auc), f4(pr), f"{r.threshold:.2f} / {thr:.2f}"]
        )
    identical = len(d["runs"]) - len(rows)
    note = f"\n\n*{identical} of {len(d['runs'])} runs are identical at log precision (not listed).*"
    return md_table(
        ["Run (differs)", "Cost macOS", "Cost Docker", "PR-AUC macOS", "PR-AUC Docker", "Thr. macOS / Docker"],
        rows, "lrrrrr",
    ) + note


TABLES = {
    "matrix": table_matrix,
    "results_val": table_results_val,
    "results_test": table_results_test,
    "champion": table_champion,
    "ablation": table_ablation,
    "splits": table_splits,
    "docker": table_docker,
}


def render(text: str, d: dict) -> str:
    for name, builder in TABLES.items():
        pattern = re.compile(rf"(<!-- BEGIN:{name} -->\n)(?:.*?\n)?(<!-- END:{name} -->)", re.S)
        if not pattern.search(text):
            raise SystemExit(f"marker for table '{name}' not found in {REPORT_MD.name}")
        text = pattern.sub(lambda m, b=builder: m.group(1) + b(d) + "\n" + m.group(2), text)
    return text


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if tables are stale")
    args = parser.parse_args()
    d = load()
    current = REPORT_MD.read_text(encoding="utf-8")
    updated = render(current, d)
    if args.check:
        if updated != current:
            print("STALE: tables differ from experiments.csv; run make_tables.py")
            return 1
        print(f"OK: {len(TABLES)} tables match experiments.csv ({len(d['runs'])} runs)")
        return 0
    REPORT_MD.write_text(updated, encoding="utf-8")
    print(f"Wrote {len(TABLES)} tables into {REPORT_MD.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
