"""Data ingestion, cleaning and splitting for the Telco churn dataset."""

from __future__ import annotations

import hashlib
import json
import logging
import urllib.request
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.model_selection import train_test_split

from src.config import PROJECT_ROOT

logger = logging.getLogger(__name__)

TARGET_COLUMN = "target"
SPLITS = ("train", "val", "test")


class DataIntegrityError(RuntimeError):
    """Raised when the raw file does not match the pinned data version."""


def relative_to_project(path: str | Path) -> str:
    """Return ``path`` relative to the project root when possible (portable manifests).

    Args:
        path: Absolute or relative path.

    Returns:
        POSIX-style relative path, or the original path if outside the project.
    """
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def sha256_file(path: str | Path, chunk_size: int = 1 << 20) -> str:
    """Compute the SHA-256 digest of a file.

    Args:
        path: File to hash.
        chunk_size: Bytes read per iteration.

    Returns:
        Hex-encoded SHA-256 digest.
    """
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ingest(config: dict[str, Any], force_download: bool = False) -> dict[str, Any]:
    """Fetch the raw CSV (if missing) and verify it against the pinned hash.

    Args:
        config: Pipeline configuration.
        force_download: Re-download even if the file already exists.

    Returns:
        Manifest with path, sha256, size and row count of the raw file.

    Raises:
        DataIntegrityError: If the file hash differs from ``data.expected_sha256``.
    """
    raw_path = Path(config["paths"]["raw_data"])
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    if force_download or not raw_path.exists():
        url = config["data"]["source_url"]
        logger.info("Downloading %s -> %s", url, raw_path)
        tmp_path = raw_path.with_suffix(".part")
        urllib.request.urlretrieve(url, tmp_path)  # noqa: S310 - pinned https URL
        tmp_path.replace(raw_path)

    digest = sha256_file(raw_path)
    expected = config["data"].get("expected_sha256")
    if expected and digest != expected:
        raise DataIntegrityError(
            f"Raw data hash mismatch: expected {expected}, got {digest}. "
            "Update data.expected_sha256 only after reviewing the new data version."
        )
    with raw_path.open(encoding="utf-8") as handle:
        n_rows = sum(1 for _ in handle) - 1
    manifest = {
        "path": relative_to_project(raw_path),
        "sha256": digest,
        "size_bytes": raw_path.stat().st_size,
        "n_rows": n_rows,
    }
    logger.info("Ingested %s rows (sha256=%s)", n_rows, digest[:12])
    return manifest


def load_raw(path: str | Path) -> pd.DataFrame:
    """Read the raw CSV keeping every column as delivered by the source.

    Args:
        path: Raw CSV path.

    Returns:
        Raw dataframe (``TotalCharges`` is still a string column).
    """
    return pd.read_csv(path, dtype={"TotalCharges": str})


def clean(df: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Fix types and encode the target.

    ``TotalCharges`` is blank for brand-new customers (``tenure == 0``); they have
    not been billed yet, so the value is set to 0 rather than imputed.

    Args:
        df: Raw dataframe.
        config: Pipeline configuration.

    Returns:
        Clean dataframe with a binary ``target`` column and no ID/raw target.
    """
    data_cfg = config["data"]
    out = df.copy()
    out["TotalCharges"] = pd.to_numeric(out["TotalCharges"].str.strip(), errors="coerce")
    new_customer = out["TotalCharges"].isna() & (out["tenure"] == 0)
    out.loc[new_customer, "TotalCharges"] = 0.0
    out[TARGET_COLUMN] = (out[data_cfg["target"]] == data_cfg["positive_label"]).astype(int)
    out = out.drop(columns=[data_cfg["target"], data_cfg["id_column"]])
    return out.reset_index(drop=True)


def split(
    df: pd.DataFrame, val_size: float, test_size: float, seed: int
) -> dict[str, pd.DataFrame]:
    """Stratified train/validation/test split.

    Args:
        df: Clean dataframe containing ``target``.
        val_size: Validation fraction of the full dataset.
        test_size: Test fraction of the full dataset.
        seed: Random seed.

    Returns:
        Mapping ``{"train", "val", "test"} -> dataframe``.
    """
    train_val, test = train_test_split(
        df, test_size=test_size, stratify=df[TARGET_COLUMN], random_state=seed
    )
    relative_val = val_size / (1.0 - test_size)
    train, val = train_test_split(
        train_val,
        test_size=relative_val,
        stratify=train_val[TARGET_COLUMN],
        random_state=seed,
    )
    return {
        "train": train.reset_index(drop=True),
        "val": val.reset_index(drop=True),
        "test": test.reset_index(drop=True),
    }


def preprocess(config: dict[str, Any]) -> dict[str, Any]:
    """Clean the raw data and write the three splits to ``paths.interim_dir``.

    Args:
        config: Pipeline configuration.

    Returns:
        Split manifest (rows, churn rate and sha256 per split).
    """
    df = clean(load_raw(config["paths"]["raw_data"]), config)
    splits = split(
        df,
        val_size=config["data"]["val_size"],
        test_size=config["data"]["test_size"],
        seed=config["project"]["seed"],
    )
    out_dir = Path(config["paths"]["interim_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {}
    for name, frame in splits.items():
        path = out_dir / f"{name}.csv"
        frame.to_csv(path, index=False)
        manifest[name] = {
            "path": relative_to_project(path),
            "rows": len(frame),
            "churn_rate": round(float(frame[TARGET_COLUMN].mean()), 4),
            "sha256": sha256_file(path),
        }
    (out_dir / "split_manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def load_split(directory: str | Path, name: str) -> pd.DataFrame:
    """Load one split written by :func:`preprocess` or the features stage.

    Args:
        directory: Directory containing ``<name>.csv``.
        name: Split name (``train``, ``val`` or ``test``).

    Returns:
        Split dataframe.
    """
    return pd.read_csv(Path(directory) / f"{name}.csv")
