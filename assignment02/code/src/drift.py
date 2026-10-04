"""Input-drift check (Population Stability Index) used to trigger early retraining.

The reference distribution is the training split of the current model; the
"current" snapshot is the latest customer extract. A PSI above the configured
threshold on any production feature marks the snapshot as drifted, which the
Airflow drift-monitor DAG turns into a dataset event that triggers retraining.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.data import clean, load_raw, load_split, relative_to_project
from src.features import BASE_CATEGORICAL, BASE_NUMERIC

logger = logging.getLogger(__name__)

EPSILON = 1e-4


def _psi(reference: np.ndarray, current: np.ndarray) -> float:
    """PSI between two proportion vectors (same bins, each summing to 1)."""
    ref = np.clip(reference, EPSILON, None)
    cur = np.clip(current, EPSILON, None)
    return float(np.sum((cur - ref) * np.log(cur / ref)))


def psi_numeric(reference: pd.Series, current: pd.Series, bins: int = 10) -> float:
    """PSI of a numeric feature using reference-quantile bins.

    Args:
        reference: Reference values.
        current: Current values.
        bins: Number of quantile bins.

    Returns:
        Population Stability Index (0 = identical distributions).
    """
    edges = np.unique(np.quantile(reference.dropna(), np.linspace(0, 1, bins + 1)))
    edges[0], edges[-1] = -np.inf, np.inf
    ref_counts = np.histogram(reference.dropna(), bins=edges)[0]
    cur_counts = np.histogram(current.dropna(), bins=edges)[0]
    return _psi(ref_counts / ref_counts.sum(), cur_counts / cur_counts.sum())


def psi_categorical(reference: pd.Series, current: pd.Series) -> float:
    """PSI of a categorical feature over the union of observed categories.

    Args:
        reference: Reference values.
        current: Current values.

    Returns:
        Population Stability Index.
    """
    ref = reference.astype(str).value_counts(normalize=True)
    cur = current.astype(str).value_counts(normalize=True)
    categories = ref.index.union(cur.index)
    return _psi(
        ref.reindex(categories, fill_value=0).to_numpy(),
        cur.reindex(categories, fill_value=0).to_numpy(),
    )


def compute_drift(
    reference: pd.DataFrame, current: pd.DataFrame, threshold: float, bins: int = 10
) -> dict[str, Any]:
    """PSI for every production feature and the overall drift decision.

    Args:
        reference: Reference frame (training split).
        current: Current snapshot (cleaned, same columns).
        threshold: PSI above which a feature counts as drifted.
        bins: Quantile bins for numeric features.

    Returns:
        Report with per-feature PSI, drifted features, ``max_psi`` and ``drift_detected``.
    """
    psi = {col: psi_numeric(reference[col], current[col], bins) for col in BASE_NUMERIC}
    psi.update({col: psi_categorical(reference[col], current[col]) for col in BASE_CATEGORICAL})
    psi = {col: round(value, 4) for col, value in sorted(psi.items(), key=lambda kv: -kv[1])}
    drifted = [col for col, value in psi.items() if value > threshold]
    return {
        "threshold": threshold,
        "max_psi": max(psi.values()),
        "drifted_features": drifted,
        "drift_detected": bool(drifted),
        "psi": psi,
    }


def run_drift_check(config: dict[str, Any], current_path: str | None = None) -> dict[str, Any]:
    """Compare the latest snapshot with the training reference and write the report.

    Args:
        config: Pipeline configuration (``drift`` and ``paths`` sections).
        current_path: Optional snapshot path overriding ``paths.drift_current_data``.

    Returns:
        Drift report (also written to ``reports/drift_report.json``).
    """
    drift_cfg = config["drift"]
    current_file = Path(current_path or config["paths"]["drift_current_data"])
    reference = load_split(config["paths"]["interim_dir"], drift_cfg["reference_split"])
    current = clean(load_raw(current_file), config)
    report = compute_drift(reference, current, drift_cfg["psi_threshold"], drift_cfg["bins"])
    report.update(
        {
            "reference": f"{drift_cfg['reference_split']} split",
            "current": relative_to_project(current_file),
            "n_reference": len(reference),
            "n_current": len(current),
        }
    )
    out = Path(config["paths"]["reports_dir"]) / "drift_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    logger.info(
        "Drift check: max PSI %.4f, drifted=%s", report["max_psi"], report["drifted_features"]
    )
    return report
