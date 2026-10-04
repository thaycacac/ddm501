"""Tests for cleaning, feature engineering and the encoding pipeline."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.data import TARGET_COLUMN, clean, split
from src.features import (
    ENGINEERED_CATEGORICAL,
    ENGINEERED_NUMERIC,
    PROTECTED_ATTRIBUTES,
    FeatureEngineer,
    add_engineered_features,
    build_preprocessor,
    check_features,
    feature_columns,
    raw_input_columns,
)


@pytest.fixture()
def clean_df(raw_df: pd.DataFrame, config: dict) -> pd.DataFrame:
    return clean(raw_df, config)


def test_clean_encodes_target_and_drops_id(clean_df: pd.DataFrame) -> None:
    assert TARGET_COLUMN in clean_df
    assert set(clean_df[TARGET_COLUMN].unique()) == {0, 1}
    assert "customerID" not in clean_df and "Churn" not in clean_df
    assert clean_df["TotalCharges"].dtype == float


def test_clean_sets_new_customer_total_charges_to_zero(raw_df: pd.DataFrame, config: dict) -> None:
    raw_df.loc[0, ["tenure", "TotalCharges"]] = [0, " "]
    out = clean(raw_df, config)
    assert out.loc[0, "TotalCharges"] == 0.0


def test_engineered_features_values(clean_df: pd.DataFrame) -> None:
    out = add_engineered_features(clean_df)
    for column in ENGINEERED_NUMERIC + ENGINEERED_CATEGORICAL:
        assert column in out
    assert out["num_addon_services"].between(0, 6).all()
    expected = clean_df["TotalCharges"] / clean_df["tenure"].clip(lower=1)
    np.testing.assert_allclose(out["avg_monthly_spend"], expected)
    assert set(out["is_month_to_month"]) <= {"Yes", "No"}
    assert check_features(out) == []


def test_zero_tenure_has_finite_features(clean_df: pd.DataFrame) -> None:
    clean_df.loc[0, ["tenure", "TotalCharges"]] = [0, 0.0]
    out = add_engineered_features(clean_df)
    assert out.loc[0, "avg_monthly_spend"] == clean_df.loc[0, "MonthlyCharges"]
    assert out.loc[0, "tenure_bucket"] == "0-6m"
    assert check_features(out) == []


def test_check_features_flags_non_finite(clean_df: pd.DataFrame) -> None:
    out = add_engineered_features(clean_df)
    out.loc[0, "charge_delta"] = np.inf
    assert check_features(out)


@pytest.mark.parametrize("feature_set", ["base", "engineered"])
def test_production_feature_sets_exclude_protected_attribute(feature_set: str) -> None:
    numeric, categorical = feature_columns(feature_set)
    for column in PROTECTED_ATTRIBUTES:
        assert column not in numeric + categorical
        assert column not in raw_input_columns(feature_set)


def test_ablation_feature_set_adds_only_gender() -> None:
    _, with_gender = feature_columns("engineered_gender")
    _, without = feature_columns("engineered")
    assert sorted(set(with_gender) - set(without)) == ["gender"]
    assert "gender" in raw_input_columns("engineered_gender")


@pytest.mark.parametrize("feature_set", ["base", "engineered", "engineered_gender"])
def test_feature_engineer_and_preprocessor(clean_df: pd.DataFrame, feature_set: str) -> None:
    raw_inputs = clean_df.drop(columns=[TARGET_COLUMN])
    frame = FeatureEngineer(feature_set).fit_transform(raw_inputs)
    numeric, categorical = feature_columns(feature_set)
    assert list(frame.columns) == numeric + categorical
    matrix = build_preprocessor(feature_set).fit_transform(frame)
    assert matrix.shape[0] == len(clean_df)
    assert np.isfinite(matrix).all()


def test_unknown_feature_set_raises() -> None:
    with pytest.raises(ValueError):
        feature_columns("unknown")


def test_split_is_stratified_and_deterministic(clean_df: pd.DataFrame) -> None:
    first = split(clean_df, val_size=0.25, test_size=0.25, seed=42)
    second = split(clean_df, val_size=0.25, test_size=0.25, seed=42)
    assert sum(len(f) for f in first.values()) == len(clean_df)
    for name in first:
        pd.testing.assert_frame_equal(first[name], second[name])
        assert first[name][TARGET_COLUMN].mean() == pytest.approx(0.25, abs=0.05)
