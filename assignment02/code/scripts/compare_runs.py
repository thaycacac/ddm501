"""Compare two pipeline executions run-by-run (reproducibility check).

Matches MLflow runs of two ``pipeline_run_id`` values by run name and reports the
largest absolute difference over every metric except wall-clock timings.

Usage:
    python scripts/compare_runs.py <pipeline_run_id_a> <pipeline_run_id_b>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import mlflow
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import load_config  # noqa: E402

TIMING_METRICS = ("train_seconds", "inference_ms_per_1k_rows")


def main() -> None:
    """CLI entry point; prints and writes ``reports/ops_evidence/reproducibility_check.json``."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("run_a")
    parser.add_argument("run_b")
    args = parser.parse_args()

    config = load_config()
    mlflow.set_tracking_uri(config["mlflow"]["tracking_uri"])
    runs = mlflow.search_runs(experiment_names=[config["mlflow"]["experiment_name"]])
    frames = {
        rid: runs[runs["tags.pipeline_run_id"] == rid].set_index("tags.mlflow.runName").sort_index()
        for rid in (args.run_a, args.run_b)
    }
    a, b = frames[args.run_a], frames[args.run_b]
    metrics = [
        c for c in runs.columns if c.startswith("metrics.") and not c.endswith(TIMING_METRICS)
    ]
    diff = (a[metrics] - b[metrics]).abs()
    result = {
        "run_a": args.run_a,
        "run_b": args.run_b,
        "n_runs": int(len(a)),
        "same_run_names": a.index.tolist() == b.index.tolist(),
        "n_metrics_compared": len(metrics),
        "max_abs_diff": float(np.nanmax(diff.to_numpy())),
        "thresholds_identical": bool((a["params.threshold"] == b["params.threshold"]).all()),
        "same_data_sha256": bool((a["tags.data_sha256"] == b["tags.data_sha256"]).all()),
    }
    out = Path(config["paths"]["reports_dir"]) / "ops_evidence" / "reproducibility_check.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
