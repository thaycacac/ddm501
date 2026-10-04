"""Command-line entry point: one sub-command per pipeline stage.

Each stage reads its inputs from files written by the previous stage and writes
a JSON state file to ``paths.state_dir``. This keeps stages independently
re-runnable (idempotent) and lets Airflow retry a single failed task.

Usage:
    python -m src.pipeline ingest|validate|preprocess|features|train|evaluate|register
    python -m src.pipeline all
    python -m src.pipeline drift [--current snapshot.csv]
    python -m src.pipeline promote --approved-by "<name>"
    python -m src.pipeline rollback --reason "<why>"
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.config import load_config, set_global_seed

logger = logging.getLogger("telco_churn.pipeline")

STAGES = ("ingest", "validate", "preprocess", "features", "train", "evaluate", "register")
# Operational commands, deliberately not part of ``all``.
OPERATIONS = ("drift", "promote", "rollback")


def _state_path(config: dict[str, Any], stage: str) -> Path:
    state_dir = Path(config["paths"]["state_dir"])
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir / f"{stage}.json"


def write_state(config: dict[str, Any], stage: str, payload: dict[str, Any]) -> None:
    """Persist a stage's output summary as JSON.

    Args:
        config: Pipeline configuration.
        stage: Stage name.
        payload: JSON-serialisable summary.
    """
    payload = {"stage": stage, "finished_at": datetime.now(UTC).isoformat(), **payload}
    _state_path(config, stage).write_text(json.dumps(payload, indent=2, default=str))


def read_state(config: dict[str, Any], stage: str) -> dict[str, Any]:
    """Load the state written by an upstream stage.

    Args:
        config: Pipeline configuration.
        stage: Upstream stage name.

    Returns:
        Parsed JSON state.

    Raises:
        FileNotFoundError: If the upstream stage has not run yet.
    """
    path = _state_path(config, stage)
    if not path.exists():
        raise FileNotFoundError(f"Upstream stage '{stage}' has no state at {path}; run it first")
    return json.loads(path.read_text())


def _pipeline_run_id(config: dict[str, Any], create: bool) -> str:
    """Resolve the id grouping MLflow runs of one execution."""
    run_id = os.environ.get("TELCO_PIPELINE_RUN_ID")
    if run_id:
        return run_id
    if create:
        return "local__" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return read_state(config, "train")["pipeline_run_id"]


def stage_ingest(config: dict[str, Any]) -> dict[str, Any]:
    """Download (if needed) and hash-verify the raw dataset."""
    from src.data import ingest

    return ingest(config)


def stage_validate(config: dict[str, Any]) -> dict[str, Any]:
    """Validate the raw dataset; raises on blocking errors."""
    from src.data import load_raw
    from src.validation import assert_valid, validate_raw

    report = validate_raw(load_raw(config["paths"]["raw_data"]), config)
    report_path = Path(config["paths"]["reports_dir"]) / "validation_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report.to_dict(), indent=2))
    assert_valid(report)
    return report.to_dict()


def stage_preprocess(config: dict[str, Any]) -> dict[str, Any]:
    """Clean and split the raw data."""
    from src.data import preprocess

    read_state(config, "validate")
    return preprocess(config)


def stage_features(config: dict[str, Any]) -> dict[str, Any]:
    """Materialise engineered features and run the feature quality gate."""
    from src.features import build_features

    return build_features(config)


def stage_train(config: dict[str, Any], only: list[str] | None = None) -> dict[str, Any]:
    """Train every configured experiment and log it to MLflow."""
    from src.train import train_all

    pipeline_run_id = _pipeline_run_id(config, create=True)
    run_ids = train_all(config, pipeline_run_id, read_state(config, "ingest"), only=only)
    return {"pipeline_run_id": pipeline_run_id, "mlflow_run_ids": run_ids}


def stage_evaluate(config: dict[str, Any]) -> dict[str, Any]:
    """Export the MLflow results table and comparison charts."""
    from src.evaluate import export_runs, plot_run_comparison

    pipeline_run_id = _pipeline_run_id(config, create=False)
    table = export_runs(config, pipeline_run_id)
    figures = plot_run_comparison(table, Path(config["paths"]["figures_dir"]))
    top = table.head(5)[
        ["run_name", "val_business_cost_per_customer", "val_pr_auc", "val_roc_auc", "val_recall"]
    ]
    return {
        "pipeline_run_id": pipeline_run_id,
        "n_runs": len(table),
        "top5": top.to_dict(orient="records"),
        "figures": [p.name for p in figures],
    }


def stage_register(config: dict[str, Any]) -> dict[str, Any]:
    """Apply the quality gates, select the challenger and register it."""
    import pandas as pd

    from src.register import register

    table = pd.read_csv(Path(config["paths"]["reports_dir"]) / "experiments.csv")
    pipeline_run_id = _pipeline_run_id(config, create=False)
    table = table[table["pipeline_run_id"] == pipeline_run_id].reset_index(drop=True)
    return register(table, config)


def run_operation(operation: str, config: dict[str, Any], args: argparse.Namespace) -> int:
    """Execute an operational command and print its JSON result.

    Args:
        operation: One of :data:`OPERATIONS`.
        config: Pipeline configuration.
        args: Parsed CLI arguments.

    Returns:
        Process exit code.
    """
    if operation == "drift":
        from src.drift import run_drift_check

        result = run_drift_check(config, args.current)
        result = {k: v for k, v in result.items() if k != "psi"}
    elif operation == "promote":
        from src.register import promote_challenger

        if not args.approved_by:
            raise SystemExit("promote requires --approved-by (human approval gate)")
        result = promote_challenger(config, args.approved_by)
    else:
        from src.register import rollback_champion

        result = rollback_champion(config, args.reason or "unspecified")
    print(json.dumps(result, indent=2, default=str))
    return 0


def run_stage(stage: str, config: dict[str, Any], only: list[str] | None = None) -> dict[str, Any]:
    """Execute one stage and persist its state.

    Args:
        stage: One of :data:`STAGES`.
        config: Pipeline configuration.
        only: Optional experiment subset for the ``train`` stage.

    Returns:
        Stage summary.
    """
    set_global_seed(int(config["project"]["seed"]))
    handlers = {
        "ingest": stage_ingest,
        "validate": stage_validate,
        "preprocess": stage_preprocess,
        "features": stage_features,
        "evaluate": stage_evaluate,
        "register": stage_register,
    }
    logger.info("stage=%s status=started", stage)
    result = stage_train(config, only) if stage == "train" else handlers[stage](config)
    write_state(config, stage, result)
    logger.info("stage=%s status=succeeded", stage)
    return result


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.

    Args:
        argv: Arguments (defaults to ``sys.argv[1:]``).

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(description="Telco churn training pipeline")
    parser.add_argument("stage", choices=[*STAGES, "all", *OPERATIONS])
    parser.add_argument("--config", default=None, help="Path to config.yaml")
    parser.add_argument("--only", nargs="*", default=None, help="Subset of experiment names")
    parser.add_argument("--current", default=None, help="drift: snapshot to compare")
    parser.add_argument("--approved-by", default=None, help="promote: approver name")
    parser.add_argument("--reason", default=None, help="rollback: reason")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    for noisy in ("mlflow", "alembic", "urllib3", "git"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    config = load_config(args.config)
    if args.stage in OPERATIONS:
        return run_operation(args.stage, config, args)
    if args.stage == "all" and not os.environ.get("TELCO_PIPELINE_RUN_ID"):
        os.environ["TELCO_PIPELINE_RUN_ID"] = _pipeline_run_id(config, create=True)
    for stage in STAGES if args.stage == "all" else (args.stage,):
        result = run_stage(stage, config, args.only)
        if stage == "register":
            print(json.dumps({k: v for k, v in result.items() if k != "metrics"}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
