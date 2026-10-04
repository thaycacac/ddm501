"""Tests for the PSI drift check that triggers early retraining."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

from src.data import clean
from src.drift import compute_drift, psi_categorical, psi_numeric

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "make_drifted_snapshot.py"


def test_psi_is_zero_for_identical_distributions() -> None:
    values = pd.Series(np.random.default_rng(0).normal(size=5000))
    assert psi_numeric(values, values) == 0.0
    labels = pd.Series(["a", "b", "b", "c"] * 100)
    assert psi_categorical(labels, labels) == 0.0


def test_psi_grows_with_shift() -> None:
    rng = np.random.default_rng(0)
    reference = pd.Series(rng.normal(size=5000))
    small = psi_numeric(reference, pd.Series(rng.normal(0.1, 1, 5000)))
    large = psi_numeric(reference, pd.Series(rng.normal(1.0, 1, 5000)))
    assert small < 0.1 < 0.2 < large


def test_simulated_snapshot_is_flagged(raw_df: pd.DataFrame, config: dict) -> None:
    spec = importlib.util.spec_from_file_location("make_drifted_snapshot", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    big = pd.concat([raw_df] * 25, ignore_index=True)
    big["customerID"] = [f"{i:05d}" for i in range(len(big))]
    reference = clean(big, config)
    same = compute_drift(reference, reference, threshold=0.2)
    assert not same["drift_detected"] and same["max_psi"] == 0.0
    drifted = compute_drift(reference, clean(module.make_drifted(big), config), threshold=0.2)
    assert drifted["drift_detected"]
    assert "MonthlyCharges" in drifted["drifted_features"]
    assert drifted["psi"]["Contract"] > same["psi"]["Contract"]
