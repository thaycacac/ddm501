"""Shared fixtures: a small synthetic raw dataset that mirrors the IBM schema."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import pytest

from src.config import load_config


@pytest.fixture()
def config() -> dict[str, Any]:
    """Project config with thresholds relaxed for tiny test frames."""
    cfg = load_config(environ={})
    cfg["validation"]["min_rows"] = 10
    return cfg


@pytest.fixture()
def raw_df() -> pd.DataFrame:
    """Forty synthetic customers (25% churn) with valid domain values."""
    rng = np.random.default_rng(0)
    n = 40
    tenure = rng.integers(1, 72, n)
    monthly = rng.uniform(20, 110, n).round(2)
    addon = ["Yes", "No", "No internet service"]
    return pd.DataFrame(
        {
            "customerID": [f"{i:04d}-ABCDE" for i in range(n)],
            "gender": rng.choice(["Male", "Female"], n),
            "SeniorCitizen": rng.integers(0, 2, n),
            "Partner": rng.choice(["Yes", "No"], n),
            "Dependents": rng.choice(["Yes", "No"], n),
            "tenure": tenure,
            "PhoneService": rng.choice(["Yes", "No"], n),
            "MultipleLines": rng.choice(["Yes", "No", "No phone service"], n),
            "InternetService": rng.choice(["DSL", "Fiber optic", "No"], n),
            "OnlineSecurity": rng.choice(addon, n),
            "OnlineBackup": rng.choice(addon, n),
            "DeviceProtection": rng.choice(addon, n),
            "TechSupport": rng.choice(addon, n),
            "StreamingTV": rng.choice(addon, n),
            "StreamingMovies": rng.choice(addon, n),
            "Contract": rng.choice(["Month-to-month", "One year", "Two year"], n),
            "PaperlessBilling": rng.choice(["Yes", "No"], n),
            "PaymentMethod": rng.choice(
                [
                    "Electronic check",
                    "Mailed check",
                    "Bank transfer (automatic)",
                    "Credit card (automatic)",
                ],
                n,
            ),
            "MonthlyCharges": monthly,
            "TotalCharges": (monthly * tenure).round(2).astype(str),
            "Churn": ["Yes"] * 10 + ["No"] * 30,
        }
    )
