"""Feature engineering shared by training and serving.

The same :class:`FeatureEngineer` is packaged inside the logged MLflow model, so
the serving path receives raw customer records and applies identical logic
(prevents training/serving skew).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.data import SPLITS, TARGET_COLUMN, load_split

logger = logging.getLogger(__name__)

BASE_NUMERIC = ["tenure", "MonthlyCharges", "TotalCharges"]
# Protected attribute: excluded from production features (privacy/fairness policy) and
# used only for fairness audits and the with-vs-without ablation experiment.
PROTECTED_ATTRIBUTES = ["gender"]
BASE_CATEGORICAL = [
    "SeniorCitizen",
    "Partner",
    "Dependents",
    "PhoneService",
    "MultipleLines",
    "InternetService",
    "OnlineSecurity",
    "OnlineBackup",
    "DeviceProtection",
    "TechSupport",
    "StreamingTV",
    "StreamingMovies",
    "Contract",
    "PaperlessBilling",
    "PaymentMethod",
]
ADDON_SERVICES = [
    "OnlineSecurity",
    "OnlineBackup",
    "DeviceProtection",
    "TechSupport",
    "StreamingTV",
    "StreamingMovies",
]
ENGINEERED_NUMERIC = ["num_addon_services", "avg_monthly_spend", "charge_delta"]
ENGINEERED_CATEGORICAL = ["tenure_bucket", "is_month_to_month", "auto_payment", "has_family"]
TENURE_BINS = [-1, 6, 12, 24, 48, np.inf]
TENURE_LABELS = ["0-6m", "7-12m", "13-24m", "25-48m", "49m+"]
FEATURE_SETS = ("base", "engineered", "engineered_gender")


def feature_columns(feature_set: str) -> tuple[list[str], list[str]]:
    """Return ``(numeric, categorical)`` model inputs for a feature set.

    Args:
        feature_set: ``"base"`` (raw attributes), ``"engineered"`` or
            ``"engineered_gender"`` (ablation only: engineered + protected attribute).

    Returns:
        Tuple of numeric and categorical column names.

    Raises:
        ValueError: If ``feature_set`` is unknown.
    """
    if feature_set == "base":
        return list(BASE_NUMERIC), list(BASE_CATEGORICAL)
    if feature_set == "engineered":
        return BASE_NUMERIC + ENGINEERED_NUMERIC, BASE_CATEGORICAL + ENGINEERED_CATEGORICAL
    if feature_set == "engineered_gender":
        return (
            BASE_NUMERIC + ENGINEERED_NUMERIC,
            BASE_CATEGORICAL + ENGINEERED_CATEGORICAL + PROTECTED_ATTRIBUTES,
        )
    raise ValueError(f"Unknown feature_set '{feature_set}', expected one of {FEATURE_SETS}")


def raw_input_columns(feature_set: str) -> list[str]:
    """Raw customer attributes the model expects as input (its serving signature).

    Args:
        feature_set: One of :data:`FEATURE_SETS`.

    Returns:
        Raw column names; the protected attribute is included only for the ablation set.
    """
    feature_columns(feature_set)
    extra = PROTECTED_ATTRIBUTES if feature_set == "engineered_gender" else []
    return BASE_NUMERIC + BASE_CATEGORICAL + extra


def add_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
    """Derive behavioural features from raw customer attributes.

    Args:
        df: Clean dataframe with the raw Telco columns.

    Returns:
        Copy of ``df`` with the engineered columns appended.
    """
    out = df.copy()
    out["num_addon_services"] = (out[ADDON_SERVICES] == "Yes").sum(axis=1).astype(float)
    # Long-run average bill; differs from MonthlyCharges when the plan changed.
    out["avg_monthly_spend"] = out["TotalCharges"] / out["tenure"].clip(lower=1)
    out.loc[out["tenure"] == 0, "avg_monthly_spend"] = out["MonthlyCharges"]
    out["charge_delta"] = out["MonthlyCharges"] - out["avg_monthly_spend"]
    out["tenure_bucket"] = pd.cut(out["tenure"], bins=TENURE_BINS, labels=TENURE_LABELS).astype(str)
    out["is_month_to_month"] = (out["Contract"] == "Month-to-month").map({True: "Yes", False: "No"})
    out["auto_payment"] = (
        out["PaymentMethod"].str.contains("automatic", regex=False).map({True: "Yes", False: "No"})
    )
    out["has_family"] = ((out["Partner"] == "Yes") | (out["Dependents"] == "Yes")).map(
        {True: "Yes", False: "No"}
    )
    return out


class FeatureEngineer(BaseEstimator, TransformerMixin):
    """Sklearn transformer that selects (and optionally derives) model inputs.

    Args:
        feature_set: ``"base"`` or ``"engineered"``.
    """

    def __init__(self, feature_set: str = "engineered") -> None:
        self.feature_set = feature_set

    def fit(self, X: pd.DataFrame, y: Any = None) -> FeatureEngineer:  # noqa: N803
        """No-op fit (stateless transformer); validates the feature set."""
        feature_columns(self.feature_set)
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:  # noqa: N803
        """Return the model input columns for ``feature_set``."""
        numeric, categorical = feature_columns(self.feature_set)
        engineered = self.feature_set.startswith("engineered")
        frame = add_engineered_features(X) if engineered else X.copy()
        frame[categorical] = frame[categorical].astype(str)
        return frame[numeric + categorical]


def build_preprocessor(feature_set: str) -> ColumnTransformer:
    """Create the encoding/scaling step for a feature set.

    Args:
        feature_set: ``"base"`` or ``"engineered"``.

    Returns:
        Unfitted ``ColumnTransformer`` (scale numeric, one-hot categorical).
    """
    numeric, categorical = feature_columns(feature_set)
    return ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), numeric),
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                categorical,
            ),
        ],
        verbose_feature_names_out=False,
    )


def check_features(frame: pd.DataFrame) -> list[str]:
    """Quality gate on materialised features.

    Args:
        frame: Output of :func:`add_engineered_features`.

    Returns:
        List of problems found (empty when the gate passes).
    """
    numeric, categorical = feature_columns("engineered")
    problems: list[str] = []
    values = frame[numeric].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        problems.append("Non-finite values in numeric features")
    if frame[categorical].isna().any().any():
        problems.append("Missing values in categorical features")
    if (frame["num_addon_services"] < 0).any() or (frame["num_addon_services"] > 6).any():
        problems.append("num_addon_services outside [0, 6]")
    return problems


def build_features(config: dict[str, Any]) -> dict[str, Any]:
    """Materialise engineered features for every split (offline analysis copy).

    Args:
        config: Pipeline configuration.

    Returns:
        Feature metadata (column lists and row counts).

    Raises:
        ValueError: If the feature quality gate fails.
    """
    interim_dir = Path(config["paths"]["interim_dir"])
    out_dir = Path(config["paths"]["processed_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    metadata: dict[str, Any] = {"feature_sets": {}, "rows": {}}
    for name in FEATURE_SETS:
        numeric, categorical = feature_columns(name)
        metadata["feature_sets"][name] = {"numeric": numeric, "categorical": categorical}
    for name in SPLITS:
        frame = add_engineered_features(load_split(interim_dir, name))
        problems = check_features(frame)
        if problems:
            raise ValueError(f"Feature quality gate failed on {name}: {problems}")
        frame.to_csv(out_dir / f"{name}.csv", index=False)
        metadata["rows"][name] = len(frame)
    metadata["target"] = TARGET_COLUMN
    (out_dir / "feature_metadata.json").write_text(json.dumps(metadata, indent=2))
    logger.info("Materialised features for %s", list(metadata["rows"]))
    return metadata
