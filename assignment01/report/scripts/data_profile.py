"""Profile the IBM Telco Customer Churn dataset and measure the current-state baselines.

Every dataset fact and baseline number quoted in the Assignment 1 report is produced by
this script and written to ``report/data/profile.json``, so the report can be regenerated
and audited.

Usage:
    python report/scripts/data_profile.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, f1_score, precision_score, recall_score, roc_auc_score

REPORT_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = REPORT_DIR / "data" / "Telco-Customer-Churn.csv"
OUT_PATH = REPORT_DIR / "data" / "profile.json"
TOP_K_FRACTION = 0.20


def load(path: Path) -> pd.DataFrame:
    """Load the raw CSV, keeping TotalCharges blanks visible for quality checks."""
    return pd.read_csv(path, dtype={"TotalCharges": str})


def quality_report(df: pd.DataFrame) -> dict:
    """Count the data-quality issues the validation stage must handle."""
    total_charges = pd.to_numeric(df["TotalCharges"].str.strip(), errors="coerce")
    return {
        "rows": int(len(df)),
        "columns": int(df.shape[1]),
        "duplicate_customer_ids": int(df["customerID"].duplicated().sum()),
        "blank_total_charges": int(total_charges.isna().sum()),
        "blank_total_charges_with_tenure_0": int((total_charges.isna() & (df["tenure"] == 0)).sum()),
        "null_cells_other_columns": int(df.drop(columns=["TotalCharges"]).isna().sum().sum()),
        "tenure_range": [int(df["tenure"].min()), int(df["tenure"].max())],
        "monthly_charges_range": [float(df["MonthlyCharges"].min()), float(df["MonthlyCharges"].max())],
        "monthly_charges_mean": round(float(df["MonthlyCharges"].mean()), 2),
        "categorical_columns": int(df.shape[1] - 2 - 3),
        "numeric_columns": 3,
    }


def churn_breakdown(df: pd.DataFrame, y: pd.Series) -> dict:
    """Churn rate overall and by the segments the current rules rely on."""
    out = {"churn_rate": round(float(y.mean()), 4), "churners": int(y.sum())}
    for col in ["Contract", "InternetService", "PaymentMethod"]:
        out[f"churn_by_{col}"] = {k: round(float(v), 4) for k, v in y.groupby(df[col]).mean().items()}
    tenure_band = pd.cut(df["tenure"], bins=[-1, 12, 24, 48, 72], labels=["0-12", "13-24", "25-48", "49-72"])
    out["churn_by_tenure_band"] = {str(k): round(float(v), 4) for k, v in y.groupby(tenure_band, observed=True).mean().items()}
    return out


def recall_at_k(y: np.ndarray, score: np.ndarray, frac: float, seed: int = 42) -> tuple[float, float]:
    """Recall and precision when contacting the top ``frac`` of customers by score.

    Ties are broken randomly (fixed seed) so a coarse rule score is not favoured by row order.
    """
    rng = np.random.default_rng(seed)
    k = int(round(frac * len(y)))
    order = np.lexsort((rng.random(len(y)), -score))[:k]
    hits = y[order].sum()
    return float(hits / y.sum()), float(hits / k)


def baselines(df: pd.DataFrame, y: pd.Series) -> dict:
    """Measure the two non-ML baselines: random targeting and the Retention team's scorecard."""
    yv = y.to_numpy()
    rng = np.random.default_rng(42)
    random_score = rng.random(len(yv))
    r_rec, r_prec = recall_at_k(yv, random_score, TOP_K_FRACTION)

    # Current-state scorecard (hypothetical rules maintained by Retention in a spreadsheet).
    scorecard = (
        2 * (df["Contract"] == "Month-to-month").astype(int)
        + 1 * (df["tenure"] <= 12).astype(int)
        + 1 * (df["PaymentMethod"] == "Electronic check").astype(int)
        + 1 * (df["InternetService"] == "Fiber optic").astype(int)
        + 1 * (df["TechSupport"] == "No").astype(int)
    ).to_numpy()
    s_rec, s_prec = recall_at_k(yv, scorecard, TOP_K_FRACTION)

    # Single binary rule used today for the monthly call list.
    rule = ((df["Contract"] == "Month-to-month") & (df["tenure"] <= 12)).astype(int).to_numpy()

    return {
        "top_k_fraction": TOP_K_FRACTION,
        "random": {
            "roc_auc": 0.5,
            "pr_auc": round(float(yv.mean()), 4),
            "recall_at_top20": round(r_rec, 4),
            "precision_at_top20": round(r_prec, 4),
        },
        "scorecard": {
            "roc_auc": round(float(roc_auc_score(yv, scorecard)), 4),
            "pr_auc": round(float(average_precision_score(yv, scorecard)), 4),
            "recall_at_top20": round(s_rec, 4),
            "precision_at_top20": round(s_prec, 4),
        },
        "binary_rule_m2m_tenure_le_12": {
            "flagged_share": round(float(rule.mean()), 4),
            "precision": round(float(precision_score(yv, rule)), 4),
            "recall": round(float(recall_score(yv, rule)), 4),
            "f1": round(float(f1_score(yv, rule)), 4),
        },
    }


# Business assumptions for the hypothetical operator (NOT measured; stated in the report).
ASSUMPTIONS = {
    "postpaid_subscribers": 400_000,
    "gross_margin": 0.60,
    "offer_cost_per_contact_usd": 50.0,
    "save_rate_contacted_churners": 0.25,
    "contact_capacity_share_per_year": 0.20,
    "ml_target_recall_at_top20": 0.50,
    "platform_cost_per_year_usd": 120_000.0,
}


def business_case(profile: dict) -> dict:
    """Translate recall@capacity into retained customers and net margin per targeting policy.

    The status-quo policy contacts customers drawn at random from the binary-rule list because
    the list (28% of base) exceeds the 20% contact capacity, so its recall@capacity equals
    rule precision * capacity / churners.
    """
    a = ASSUMPTIONS
    churn_rate = profile["target"]["churn_rate"]
    arpu = profile["quality"]["monthly_charges_mean"]
    n = a["postpaid_subscribers"]
    churners = churn_rate * n
    capacity = a["contact_capacity_share_per_year"] * n
    margin_per_saved = arpu * 12 * a["gross_margin"]
    campaign_cost = capacity * a["offer_cost_per_contact_usd"]
    rule_precision = profile["baselines"]["binary_rule_m2m_tenure_le_12"]["precision"]

    policies = {
        "random": profile["baselines"]["random"]["recall_at_top20"],
        "status_quo_binary_rule": rule_precision * capacity / churners,
        "improved_scorecard": profile["baselines"]["scorecard"]["recall_at_top20"],
        "ml_target": a["ml_target_recall_at_top20"],
    }
    out: dict = {
        "assumptions": a,
        "derived": {
            "arpu_usd_month": arpu,
            "churners_per_year": round(churners),
            "contacts_per_year": round(capacity),
            "margin_per_saved_customer_usd": round(margin_per_saved, 2),
            "campaign_cost_usd": round(campaign_cost),
            "break_even_precision": round(a["offer_cost_per_contact_usd"] / (a["save_rate_contacted_churners"] * margin_per_saved), 4),
        },
        "policies": {},
    }
    for name, recall in policies.items():
        saved = recall * churners * a["save_rate_contacted_churners"]
        value = saved * margin_per_saved
        out["policies"][name] = {
            "recall_at_capacity": round(recall, 4),
            "precision_at_capacity": round(recall * churners / capacity, 4),
            "customers_saved": round(saved),
            "retained_margin_usd": round(value),
            "net_usd": round(value - campaign_cost),
            "roi": round((value - campaign_cost) / campaign_cost, 3),
            "churn_rate_after": round((churners - saved) / n, 4),
        }
    sq = out["policies"]["status_quo_binary_rule"]
    for name, p in out["policies"].items():
        p["net_vs_status_quo_usd"] = p["net_usd"] - sq["net_usd"]
        p["saved_vs_status_quo"] = p["customers_saved"] - sq["customers_saved"]
    return out


def main() -> None:
    df = load(DATA_PATH)
    y = (df["Churn"] == "Yes").astype(int)
    profile = {
        "source": "IBM Telco Customer Churn (GitHub: IBM/telco-customer-churn-on-icp4d; identical Kaggle mirror: blastchar/telco-customer-churn)",
        "quality": quality_report(df),
        "target": churn_breakdown(df, y),
        "baselines": baselines(df, y),
    }
    profile["business_case"] = business_case(profile)
    OUT_PATH.write_text(json.dumps(profile, indent=2))
    print(json.dumps(profile, indent=2))


if __name__ == "__main__":
    main()
