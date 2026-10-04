"""Create a SIMULATED drifted customer snapshot to exercise the drift-trigger path.

Scenario (synthetic, for testing only): a competitor price war moves 35% of
one/two-year contract customers to month-to-month and raises monthly charges by
12%. The output keeps the raw IBM schema so it passes the validation gate.

Usage:
    python scripts/make_drifted_snapshot.py [--out data/simulated/drifted_snapshot.csv]
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def make_drifted(raw: pd.DataFrame, seed: int = 42) -> pd.DataFrame:
    """Apply the simulated contract/price shift to a raw snapshot.

    Args:
        raw: Raw IBM Telco dataframe (``TotalCharges`` as string).
        seed: Random seed for the contract switch.

    Returns:
        Drifted copy with the same columns and dtypes.
    """
    rng = np.random.default_rng(seed)
    out = raw.copy()
    long_contract = out["Contract"] != "Month-to-month"
    switch = long_contract & (rng.uniform(size=len(out)) < 0.35)
    out.loc[switch, "Contract"] = "Month-to-month"
    out["MonthlyCharges"] = (out["MonthlyCharges"] * 1.12).round(2)
    return out


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--src", type=Path, default=PROJECT_ROOT / "data/raw/Telco-Customer-Churn.csv"
    )
    parser.add_argument(
        "--out", type=Path, default=PROJECT_ROOT / "data/simulated/drifted_snapshot.csv"
    )
    args = parser.parse_args()
    raw = pd.read_csv(args.src, dtype={"TotalCharges": str})
    args.out.parent.mkdir(parents=True, exist_ok=True)
    make_drifted(raw).to_csv(args.out, index=False)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
