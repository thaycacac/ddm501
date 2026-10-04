"""Check that A2_report.md only contains numbers and code that exist in the repository.

1. Tables: every generated table equals a fresh render from experiments.csv.
2. Code: every line of a listing tagged ``file="..."`` exists in that source file
   (lines starting with ``...`` or ``# ...`` mark omissions and are skipped).
3. Prose: every number written with 3+ decimals (or in scientific notation) outside
   tables and code matches a value in the exported evidence, an A1 constant, or a
   value derived from them below (with its formula).

Usage:
    python report/scripts/verify_numbers.py     # exit 1 on any mismatch
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_tables  # noqa: E402

CODE = make_tables.CODE_DIR
EVIDENCE_JSON = [
    "reports/challenger.json",
    "reports/champion.json",
    "reports/validation_report.json",
    "reports/pipeline_state/preprocess.json",
    "reports/ops_evidence/drift_report_simulated.json",
    "reports/ops_evidence/drift_report_current.json",
    "reports/ops_evidence/reproducibility_check.json",
]
# Assignment 1 measured baselines / goals quoted in the text (A1 Sections 1.3, 3.4).
A1_CONSTANTS = {0.476: "scorecard Recall@top-20%", 0.210: "random Recall@top-20%",
                0.005: "A1 simplicity rule (Recall@top-20%)"}


def numbers_in(obj) -> list[float]:
    if isinstance(obj, dict):
        return [n for v in obj.values() for n in numbers_in(v)]
    if isinstance(obj, list):
        return [n for v in obj for n in numbers_in(v)]
    if isinstance(obj, bool):
        return []
    if isinstance(obj, (int, float)):
        return [float(obj)]
    if isinstance(obj, str):
        try:
            return [float(obj)]
        except ValueError:
            return []
    return []


def allowed_values(d: dict) -> dict[float, str]:
    allowed: dict[float, str] = {}
    runs = d["runs"]
    for col in runs.select_dtypes("number").columns:
        for v in runs[col].dropna():
            allowed.setdefault(float(v), f"experiments.csv:{col}")
    for rel in EVIDENCE_JSON:
        for v in numbers_in(json.loads((CODE / rel).read_text())):
            allowed.setdefault(v, rel)
    for v in numbers_in(yaml.safe_load((CODE / "configs/config.yaml").read_text())):
        allowed.setdefault(v, "config.yaml")
    for name, (pr, cost, thr) in d["docker"].items():
        allowed.setdefault(pr, f"docker_train.log:{name}")
    allowed.update({k: f"A1: {v}" for k, v in A1_CONSTANTS.items()})

    r = runs.set_index("run_name")
    b = d["config"]["business"]
    val = runs.iloc[0]
    derived = {
        # break-even probability = offer_cost / (save_rate * churn_loss)
        b["offer_cost"] / (b["offer_success_rate"] * b["churn_loss"]): "break-even",
        # top-3 validation cost spread
        float(runs["val_business_cost_per_customer"].iloc[2] - val["val_business_cost_per_customer"]): "top-3 spread",
        # no-campaign validation cost per customer = churners / n * churn_loss
        374 / 1409 * b["churn_loss"]: "no-campaign cost",
    }
    for a, g in (("lr_eng_costthr", "lr_eng_gender_costthr"), ("rf_tuned_eng_costthr", "rf_tuned_eng_gender_costthr")):
        for m in ("val_business_cost_per_customer", "test_business_cost_per_customer", "val_pr_auc", "test_pr_auc"):
            derived[abs(float(r.loc[g, m] - r.loc[a, m]))] = f"ablation delta {m}"
    for name, (pr, _, _) in d["docker"].items():
        derived[abs(float(r.loc[name, "val_pr_auc"]) - pr)] = f"docker PR-AUC delta {name}"
    allowed.update({k: f"derived: {v}" for k, v in derived.items()})
    return allowed


def check_tables(text: str, d: dict) -> list[str]:
    return [] if make_tables.render(text, d) == text else ["generated tables are stale (run make_tables.py)"]


def check_code(text: str) -> list[str]:
    problems = []
    for attrs, body in re.findall(r"```\{([^}]*)\}\n(.*?)```", text, flags=re.S):
        m = re.search(r'file="([^"]+)"', attrs)
        if not m:
            continue
        source = {line.strip() for line in (CODE / m.group(1)).read_text().splitlines()}
        for line in body.splitlines():
            s = line.strip()
            if not s or s.startswith("...") or s.startswith("# ..."):
                continue
            if s not in source:
                problems.append(f"{m.group(1)}: line not in source: {s}")
    return problems


def prose(text: str) -> str:
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"<!-- BEGIN:(\w+) -->.*?<!-- END:\1 -->", "", text, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return text


def check_prose(text: str, allowed: dict[float, str]) -> tuple[list[str], int]:
    problems, count = [], 0
    for token in re.findall(r"(?<![\w.])\d+\.\d+e-\d+|(?<![\w.])\d+\.\d{3,}(?![\d.])", prose(text)):
        count += 1
        value = float(token)
        if "e" in token:
            ok = any(abs(v - value) <= abs(value) * 0.01 for v in allowed if v)
        else:
            decimals = len(token.split(".")[1])
            tol = 0.5 * 10 ** (-decimals) + 1e-9
            ok = any(abs(v - value) <= tol for v in allowed)
        if not ok:
            problems.append(f"prose number not traceable: {token}")
    return problems, count


def main() -> int:
    d = make_tables.load()
    text = make_tables.REPORT_MD.read_text(encoding="utf-8")
    allowed = allowed_values(d)
    problems = check_tables(text, d) + check_code(text)
    prose_problems, n_numbers = check_prose(text, allowed)
    problems += prose_problems
    n_listings = len(re.findall(r'```\{[^}]*file="', text))
    if problems:
        print("\n".join(problems))
        return 1
    print(
        f"OK: {len(make_tables.TABLES)} tables match experiments.csv; {n_listings} listings match "
        f"their source files; {n_numbers} prose numbers traceable to evidence"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
