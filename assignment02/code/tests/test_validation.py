"""Tests for the raw-data validation gate."""

from __future__ import annotations

import pandas as pd
import pytest

from src.validation import DataValidationError, assert_valid, validate_raw


def test_valid_data_passes(raw_df: pd.DataFrame, config: dict) -> None:
    report = validate_raw(raw_df, config)
    assert report.passed, report.errors
    assert report.stats["churn_rate"] == 0.25
    assert_valid(report)


def test_missing_column_fails(raw_df: pd.DataFrame, config: dict) -> None:
    report = validate_raw(raw_df.drop(columns=["Contract"]), config)
    assert not report.passed
    assert "Missing columns" in report.errors[0]


def test_duplicate_ids_fail(raw_df: pd.DataFrame, config: dict) -> None:
    raw_df.loc[1, "customerID"] = raw_df.loc[0, "customerID"]
    report = validate_raw(raw_df, config)
    assert any("duplicated" in e for e in report.errors)


def test_unexpected_category_fails(raw_df: pd.DataFrame, config: dict) -> None:
    raw_df.loc[0, "Contract"] = "Three year"
    report = validate_raw(raw_df, config)
    assert any("Contract" in e for e in report.errors)
    with pytest.raises(DataValidationError):
        assert_valid(report)


def test_out_of_range_numeric_fails(raw_df: pd.DataFrame, config: dict) -> None:
    raw_df.loc[0, "MonthlyCharges"] = -5.0
    report = validate_raw(raw_df, config)
    assert any("MonthlyCharges" in e for e in report.errors)


def test_blank_total_charges_for_new_customer_is_warning(
    raw_df: pd.DataFrame, config: dict
) -> None:
    raw_df.loc[0, ["tenure", "TotalCharges"]] = [0, " "]
    config["validation"]["max_missing_fraction"] = 0.05
    report = validate_raw(raw_df, config)
    assert report.passed, report.errors
    assert any("blank TotalCharges" in w for w in report.warnings)


def test_blank_total_charges_with_tenure_fails(raw_df: pd.DataFrame, config: dict) -> None:
    raw_df.loc[0, ["tenure", "TotalCharges"]] = [12, " "]
    config["validation"]["max_missing_fraction"] = 0.05
    report = validate_raw(raw_df, config)
    assert any("tenure > 0" in e for e in report.errors)


def test_churn_rate_drift_fails(raw_df: pd.DataFrame, config: dict) -> None:
    raw_df["Churn"] = "No"
    report = validate_raw(raw_df, config)
    assert any("Churn rate" in e for e in report.errors)


def test_too_few_rows_fails(raw_df: pd.DataFrame, config: dict) -> None:
    config["validation"]["min_rows"] = 1000
    report = validate_raw(raw_df, config)
    assert any("Too few rows" in e for e in report.errors)
