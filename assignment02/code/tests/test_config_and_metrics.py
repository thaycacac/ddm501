"""Tests for config overrides, business/fairness metrics and challenger selection."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.config import apply_env_overrides, load_config
from src.evaluate import business_cost, cost_optimal_threshold, recall_gap, top_k_metrics
from src.register import QualityGateError, gate_report, select_challenger

BUSINESS = {"churn_loss": 466.27, "offer_cost": 50.0, "offer_success_rate": 0.25}


def test_env_override_parses_yaml_types() -> None:
    cfg = {"project": {"seed": 42}, "mlflow": {"tracking_uri": "sqlite:///a.db"}}
    out = apply_env_overrides(
        cfg,
        {"TELCO__PROJECT__SEED": "7", "TELCO__MLFLOW__TRACKING_URI": "http://mlflow:5000"},
    )
    assert out["project"]["seed"] == 7
    assert out["mlflow"]["tracking_uri"] == "http://mlflow:5000"
    assert cfg["project"]["seed"] == 42


def test_load_config_resolves_paths() -> None:
    cfg = load_config(environ={})
    assert cfg["paths"]["raw_data"].endswith("data/raw/Telco-Customer-Churn.csv")
    assert cfg["mlflow"]["tracking_uri"].startswith("sqlite:////")
    assert len(cfg["experiments"]) >= 10


def test_business_assumptions_match_assignment_1() -> None:
    business = load_config(environ={})["business"]
    break_even = business["offer_cost"] / (business["offer_success_rate"] * business["churn_loss"])
    assert break_even == pytest.approx(0.429, abs=0.001)


def test_business_cost_matches_hand_calculation() -> None:
    y_true = np.array([1, 1, 0, 0])
    y_pred = np.array([1, 0, 1, 0])  # TP, FN, FP, TN
    result = business_cost(y_true, y_pred, BUSINESS)
    expected_total = (50 + 0.75 * 466.27) + 466.27 + 50
    assert result["business_cost"] == pytest.approx(expected_total)
    no_campaign = 2 * 466.27
    assert result["net_savings_per_1k"] == pytest.approx((no_campaign - expected_total) / 4 * 1000)


def test_top_k_lift() -> None:
    y_true = np.array([1, 0, 0, 0, 1, 0, 0, 0, 0, 0])
    y_score = np.linspace(1, 0, 10)
    result = top_k_metrics(y_true, y_score, 0.2)
    assert result["precision_at_top_k"] == 0.5
    assert result["lift_at_top_k"] == pytest.approx(2.5)
    assert result["recall_at_top_k"] == 0.5


def _calibrated(n: int = 20000) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(0)
    y_score = rng.uniform(0, 1, n)
    return (rng.uniform(0, 1, n) < y_score).astype(int), y_score


def test_cost_optimal_threshold_near_break_even() -> None:
    y_true, y_score = _calibrated()
    # Calibrated scores: contact when p * 0.25 * 466.27 > 50  ->  p > 0.429.
    assert cost_optimal_threshold(y_true, y_score, BUSINESS) == pytest.approx(0.429, abs=0.04)


def test_cost_optimal_threshold_respects_capacity() -> None:
    y_true, y_score = _calibrated()
    threshold = cost_optimal_threshold(y_true, y_score, BUSINESS, max_contact_rate=0.20)
    assert (y_score >= threshold).mean() <= 0.20
    assert threshold == pytest.approx(0.80, abs=0.02)


def test_recall_gap_and_confidence_bound() -> None:
    y_true = np.array([1] * 100 + [1] * 100)
    y_pred = np.array([1] * 80 + [0] * 20 + [1] * 60 + [0] * 40)
    groups = np.array(["F"] * 100 + ["M"] * 100)
    gap, lower = recall_gap(y_true, y_pred, groups)
    assert gap == pytest.approx(0.20)
    std_err = np.sqrt(0.8 * 0.2 / 100 + 0.6 * 0.4 / 100)
    assert lower == pytest.approx(0.20 - 1.645 * std_err)
    assert recall_gap(y_true, y_pred, np.array(["F"] * 200)) == (0.0, 0.0)


def _table() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "run_name": ["lr_baseline", "rf_a", "lr_b", "xgb_c", "ablation", "flood"],
            "model": [
                "logistic_regression",
                "random_forest",
                "logistic_regression",
                "xgboost",
                "logistic_regression",
                "lightgbm",
            ],
            "eligible": [True, True, True, True, False, True],
            "val_business_cost_per_customer": [120.0, 110.0, 110.1, 100.0, 90.0, 95.0],
            "val_pr_auc": [0.62, 0.66, 0.65, 0.70, 0.70, 0.66],
            "val_roc_auc": [0.835, 0.84, 0.84, 0.82, 0.85, 0.84],
            "val_recall_at_top_k": [0.50, 0.50, 0.50, 0.50, 0.52, 0.50],
            "val_contact_rate": [0.21, 0.20, 0.19, 0.20, 0.20, 0.40],
            "val_gender_recall_gap_lcb": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            "val_brier": [0.14, 0.14, 0.14, 0.14, 0.14, 0.14],
        }
    )


def test_gate_report_flags_each_rule(config: dict) -> None:
    checks = gate_report(_table(), config).set_index(_table()["run_name"])
    assert not checks.loc["ablation", "eligible"]
    assert not checks.loc["xgb_c", "val_roc_auc>=0.83"]
    assert not checks.loc["flood", "val_contact_rate<=0.2"]
    assert not checks.loc["lr_baseline", "beats_baseline"]
    assert checks["passed"].tolist() == [False, True, True, False, False, False]


def test_select_challenger_prefers_simpler_model_on_near_tie(config: dict) -> None:
    challenger = select_challenger(_table(), config)
    # rf_a is $0.10 cheaper, within the $0.15 tolerance, so the simpler LR wins.
    assert challenger["run_name"] == "lr_b"
    config["selection"]["simplicity_tolerance"] = 0.0
    assert select_challenger(_table(), config)["run_name"] == "rf_a"


def test_select_challenger_raises_when_nothing_passes(config: dict) -> None:
    config["selection"]["gates"]["val_roc_auc"] = 0.99
    with pytest.raises(QualityGateError):
        select_challenger(_table(), config)
