"""Raw-data validation (quality gate before any transformation)."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

EXPECTED_COLUMNS: dict[str, str] = {
    "customerID": "string",
    "gender": "string",
    "SeniorCitizen": "integer",
    "Partner": "string",
    "Dependents": "string",
    "tenure": "integer",
    "PhoneService": "string",
    "MultipleLines": "string",
    "InternetService": "string",
    "OnlineSecurity": "string",
    "OnlineBackup": "string",
    "DeviceProtection": "string",
    "TechSupport": "string",
    "StreamingTV": "string",
    "StreamingMovies": "string",
    "Contract": "string",
    "PaperlessBilling": "string",
    "PaymentMethod": "string",
    "MonthlyCharges": "float",
    "TotalCharges": "string",
    "Churn": "string",
}

# Logical types, so the check works for both pandas 2 (object) and 3 (str) dtypes.
DTYPE_CHECKS: dict[str, Callable[[pd.Series], bool]] = {
    "string": lambda s: pd.api.types.is_string_dtype(s) or pd.api.types.is_object_dtype(s),
    "integer": pd.api.types.is_integer_dtype,
    "float": pd.api.types.is_numeric_dtype,
}

YES_NO = {"Yes", "No"}
INTERNET_ADDON = {"Yes", "No", "No internet service"}
ALLOWED_VALUES: dict[str, set[Any]] = {
    "gender": {"Male", "Female"},
    "SeniorCitizen": {0, 1},
    "Partner": YES_NO,
    "Dependents": YES_NO,
    "PhoneService": YES_NO,
    "MultipleLines": {"Yes", "No", "No phone service"},
    "InternetService": {"DSL", "Fiber optic", "No"},
    "OnlineSecurity": INTERNET_ADDON,
    "OnlineBackup": INTERNET_ADDON,
    "DeviceProtection": INTERNET_ADDON,
    "TechSupport": INTERNET_ADDON,
    "StreamingTV": INTERNET_ADDON,
    "StreamingMovies": INTERNET_ADDON,
    "Contract": {"Month-to-month", "One year", "Two year"},
    "PaperlessBilling": YES_NO,
    "PaymentMethod": {
        "Electronic check",
        "Mailed check",
        "Bank transfer (automatic)",
        "Credit card (automatic)",
    },
    "Churn": YES_NO,
}


class DataValidationError(ValueError):
    """Raised when one or more blocking validation checks fail."""


@dataclass
class ValidationReport:
    """Outcome of :func:`validate_raw`.

    Attributes:
        passed: True when no blocking check failed.
        errors: Blocking failures (stop the pipeline).
        warnings: Non-blocking findings worth reviewing.
        stats: Summary statistics recorded for lineage.
    """

    passed: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)

    def fail(self, message: str) -> None:
        """Record a blocking failure."""
        self.passed = False
        self.errors.append(message)

    def to_dict(self) -> dict[str, Any]:
        """Serialise the report to a JSON-compatible dict."""
        return asdict(self)


def validate_raw(df: pd.DataFrame, config: dict[str, Any]) -> ValidationReport:
    """Run schema, domain, range and distribution checks on the raw dataframe.

    Args:
        df: Raw dataframe as returned by :func:`src.data.load_raw`.
        config: Pipeline configuration (``validation`` section).

    Returns:
        A :class:`ValidationReport`; callers decide whether to raise.
    """
    rules = config["validation"]
    report = ValidationReport()
    report.stats["n_rows"] = int(len(df))

    missing_cols = sorted(set(EXPECTED_COLUMNS) - set(df.columns))
    if missing_cols:
        report.fail(f"Missing columns: {missing_cols}")
        return report
    extra_cols = sorted(set(df.columns) - set(EXPECTED_COLUMNS))
    if extra_cols:
        report.warnings.append(f"Unexpected columns ignored: {extra_cols}")

    if len(df) < rules["min_rows"]:
        report.fail(f"Too few rows: {len(df)} < {rules['min_rows']}")

    id_col = config["data"]["id_column"]
    n_dup = int(df[id_col].duplicated().sum())
    report.stats["duplicate_ids"] = n_dup
    if n_dup:
        report.fail(f"{n_dup} duplicated {id_col} values")

    for column, expected_kind in EXPECTED_COLUMNS.items():
        if not DTYPE_CHECKS[expected_kind](df[column]):
            report.fail(f"Column {column} has dtype {df[column].dtype}, expected {expected_kind}")

    for column, allowed in ALLOWED_VALUES.items():
        unexpected = set(df[column].dropna().unique()) - allowed
        if unexpected:
            report.fail(f"Column {column} has unexpected values {sorted(map(str, unexpected))}")

    total_charges = pd.to_numeric(df["TotalCharges"].astype(str).str.strip(), errors="coerce")
    numeric = df[["tenure", "MonthlyCharges"]].assign(TotalCharges=total_charges)
    missing_fraction = numeric.isna().mean().to_dict()
    missing_fraction.update(df.drop(columns=["TotalCharges"]).isna().mean().to_dict())
    report.stats["missing_fraction"] = {
        k: round(float(v), 5) for k, v in missing_fraction.items() if v
    }
    for column, fraction in missing_fraction.items():
        if fraction > rules["max_missing_fraction"]:
            report.fail(f"Column {column} missing fraction {fraction:.4f} too high")

    blank_tc = total_charges.isna()
    unexplained = int((blank_tc & (df["tenure"] != 0)).sum())
    if blank_tc.any():
        report.warnings.append(
            f"{int(blank_tc.sum())} blank TotalCharges (new customers, tenure=0) -> set to 0"
        )
    if unexplained:
        report.fail(f"{unexplained} blank TotalCharges rows with tenure > 0")

    for column, (low, high) in rules["numeric_ranges"].items():
        values = numeric[column].dropna()
        out_of_range = int(((values < low) | (values > high)).sum())
        if out_of_range:
            report.fail(f"{out_of_range} values of {column} outside [{low}, {high}]")

    churn_rate = float((df["Churn"] == config["data"]["positive_label"]).mean())
    report.stats["churn_rate"] = round(churn_rate, 4)
    low, high = rules["churn_rate_range"]
    if not low <= churn_rate <= high:
        report.fail(f"Churn rate {churn_rate:.3f} outside expected range [{low}, {high}]")

    logger.info(
        "Validation %s: %d errors, %d warnings",
        "passed" if report.passed else "FAILED",
        len(report.errors),
        len(report.warnings),
    )
    return report


def assert_valid(report: ValidationReport) -> None:
    """Raise if the report contains blocking errors.

    Args:
        report: Result of :func:`validate_raw`.

    Raises:
        DataValidationError: When ``report.passed`` is False.
    """
    if not report.passed:
        raise DataValidationError("; ".join(report.errors))
