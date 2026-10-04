"""Challenger selection, quality gates and MLflow Model Registry alias management.

The automated pipeline only ever moves the ``@challenger`` alias. Promotion to
``@champion`` (what serving loads) is a separate, human-approved command, and a
rollback restores ``@previous_champion``.
"""

from __future__ import annotations

import json
import logging
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import mlflow
import pandas as pd
from mlflow import MlflowClient

logger = logging.getLogger(__name__)


class QualityGateError(RuntimeError):
    """Raised when no candidate passes the promotion gates."""


class RegistryStateError(RuntimeError):
    """Raised when a promotion/rollback is requested but the required alias is missing."""


def _is_eligible(table: pd.DataFrame) -> pd.Series:
    """Rows allowed to become challenger (ablation runs are logged with ``eligible=false``)."""
    if "eligible" not in table:
        return pd.Series(True, index=table.index)
    return table["eligible"].astype(str).str.lower().isin(["true", "1"])


def gate_report(table: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Evaluate every gate for every run (used for selection and for the report).

    Args:
        table: Experiment table produced by :func:`src.evaluate.export_runs`.
        config: Pipeline configuration (``selection`` section).

    Returns:
        Boolean frame indexed like ``table``: one column per gate plus ``eligible``,
        ``beats_baseline`` and ``passed`` (all conditions true).
    """
    selection = config["selection"]
    metric, mode = selection["metric"], selection["mode"]
    checks = pd.DataFrame(index=table.index)
    checks["eligible"] = _is_eligible(table)
    for gate_metric, minimum in selection.get("gates", {}).items():
        checks[f"{gate_metric}>={minimum}"] = table[gate_metric] >= minimum
    for gate_metric, maximum in selection.get("max_gates", {}).items():
        checks[f"{gate_metric}<={maximum}"] = table[gate_metric] <= maximum

    baseline = table[table["run_name"] == selection["baseline_experiment"]]
    if baseline.empty:
        checks["beats_baseline"] = True
    else:
        base_value = float(baseline.iloc[0][metric])
        better = table[metric] < base_value if mode == "min" else table[metric] > base_value
        checks["beats_baseline"] = better
    checks["passed"] = checks.all(axis=1)
    return checks


def select_challenger(table: pd.DataFrame, config: dict[str, Any]) -> pd.Series:
    """Choose the challenger: best gate-passing run, preferring simpler models on near-ties.

    Selection uses validation metrics only; test metrics are reported but never
    used for the decision (avoids optimistic bias). Among candidates within
    ``simplicity_tolerance`` of the best selection metric, the model family that is
    earliest in ``complexity_order`` wins (then the metric, then the tie-breaker).

    Args:
        table: Experiment table produced by :func:`src.evaluate.export_runs`.
        config: Pipeline configuration (``selection`` section).

    Returns:
        Row of ``table`` for the challenger run, with a ``selection_reason`` entry.

    Raises:
        QualityGateError: If no run satisfies the gates.
    """
    selection = config["selection"]
    metric, mode = selection["metric"], selection["mode"]
    checks = gate_report(table, config)
    candidates = table[checks["passed"]].copy()
    if candidates.empty:
        raise QualityGateError(
            f"No eligible run passed gates {selection.get('gates')} / "
            f"{selection.get('max_gates')} and beat the baseline on {metric}"
        )

    best = candidates[metric].min() if mode == "min" else candidates[metric].max()
    tolerance = float(selection.get("simplicity_tolerance", 0.0))
    distance = (candidates[metric] - best).abs()
    near_best = candidates[distance <= tolerance + 1e-12].copy()
    order = {name: rank for rank, name in enumerate(selection.get("complexity_order", []))}
    near_best["_complexity"] = near_best["model"].map(order).fillna(len(order))
    near_best = near_best.sort_values(
        ["_complexity", metric, selection["tie_breaker"]],
        ascending=[True, mode == "min", False],
    )
    challenger = near_best.iloc[0].drop("_complexity")
    challenger["selection_reason"] = (
        f"{len(candidates)} of {len(table)} runs passed all gates; "
        f"{len(near_best)} within {tolerance} of the best {metric} ({best:.4f}); "
        f"simplest family among them: {challenger['model']}"
    )
    return challenger


def _client(config: dict[str, Any]) -> MlflowClient:
    mlflow.set_tracking_uri(config["mlflow"]["tracking_uri"])
    return MlflowClient()


def _alias_version(client: MlflowClient, name: str, alias: str) -> str | None:
    """Return the version behind ``name@alias`` or ``None`` if the alias is unset."""
    try:
        return client.get_model_version_by_alias(name, alias).version
    except mlflow.exceptions.MlflowException:
        return None


def register_challenger(challenger: pd.Series, config: dict[str, Any]) -> dict[str, Any]:
    """Register the challenger as a new model version and point ``@challenger`` at it.

    Args:
        challenger: Row returned by :func:`select_challenger`.
        config: Pipeline configuration.

    Returns:
        Summary with model name, version, alias and key metrics.
    """
    mlflow_cfg = config["mlflow"]
    client = _client(config)
    name, alias = mlflow_cfg["registered_model_name"], mlflow_cfg["challenger_alias"]

    run = client.get_run(challenger["run_id"])
    model_uri = run.data.tags.get("model_uri", f"runs:/{challenger['run_id']}/model")
    try:
        client.get_registered_model(name)
    except mlflow.exceptions.MlflowException:
        client.create_registered_model(
            name,
            description="ChurnGuard: 12-month churn propensity model used by the Retention team.",
            tags={"owner": "retention-ml", "task": "binary-classification"},
        )

    version = mlflow.register_model(model_uri, name, tags={"run_name": challenger["run_name"]})
    version_tags = {
        "val_business_cost_per_customer": challenger["val_business_cost_per_customer"],
        "val_recall_at_top_k": challenger["val_recall_at_top_k"],
        "val_roc_auc": challenger["val_roc_auc"],
        "val_pr_auc": challenger["val_pr_auc"],
        "test_recall_at_top_k": challenger["test_recall_at_top_k"],
        "test_roc_auc": challenger["test_roc_auc"],
        "threshold": run.data.params.get("threshold"),
        "feature_set": challenger["feature_set"],
        "data_sha256": challenger["data_sha256"],
        "git_sha": challenger.get("git_sha", "unknown"),
        "pipeline_run_id": challenger["pipeline_run_id"],
        "validation_status": "passed",
        "approval_status": "pending",
    }
    for key, value in version_tags.items():
        client.set_model_version_tag(name, version.version, key, str(value))
    client.update_model_version(
        name,
        version.version,
        description=(
            f"Challenger from run '{challenger['run_name']}' "
            f"(pipeline {challenger['pipeline_run_id']}). {challenger['selection_reason']}."
        ),
    )
    client.set_registered_model_alias(name, alias, version.version)

    summary = {
        "registered_model_name": name,
        "version": int(version.version),
        "alias": alias,
        "champion_version": _alias_version(client, name, mlflow_cfg["champion_alias"]),
        "run_id": challenger["run_id"],
        "run_name": challenger["run_name"],
        "model_uri": f"models:/{name}@{alias}",
        "threshold": float(run.data.params.get("threshold", 0.5)),
        "selection_reason": challenger["selection_reason"],
        "metrics": {
            k: float(challenger[k])
            for k in challenger.index
            if k.startswith(("val_", "test_", "cv_")) and pd.notna(challenger[k])
        },
    }
    logger.info("Registered %s v%s with alias @%s", name, version.version, alias)
    return summary


def promote_challenger(config: dict[str, Any], approved_by: str) -> dict[str, Any]:
    """Human-approved promotion: ``@champion`` <- ``@challenger``.

    The former champion (if any) keeps the ``@previous_champion`` alias so that a
    rollback is a single alias switch.

    Args:
        config: Pipeline configuration.
        approved_by: Name of the approver, stored as a model-version tag.

    Returns:
        Summary of the new champion (also written to ``reports/champion.json``).

    Raises:
        RegistryStateError: If no challenger is registered.
    """
    mlflow_cfg = config["mlflow"]
    client = _client(config)
    name = mlflow_cfg["registered_model_name"]
    challenger = _alias_version(client, name, mlflow_cfg["challenger_alias"])
    if challenger is None:
        raise RegistryStateError(f"{name} has no @{mlflow_cfg['challenger_alias']} to promote")
    previous = _alias_version(client, name, mlflow_cfg["champion_alias"])

    if previous and previous != challenger:
        client.set_registered_model_alias(name, mlflow_cfg["previous_alias"], previous)
    client.set_registered_model_alias(name, mlflow_cfg["champion_alias"], challenger)
    now = datetime.now(UTC).isoformat()
    for key, value in {
        "approval_status": "approved",
        "approved_by": approved_by,
        "approved_at": now,
    }.items():
        client.set_model_version_tag(name, challenger, key, value)
    return _write_champion(client, config, name, challenger, previous, action="promote")


def rollback_champion(config: dict[str, Any], reason: str) -> dict[str, Any]:
    """Restore ``@champion`` to the ``@previous_champion`` version.

    Args:
        config: Pipeline configuration.
        reason: Why the rollback happened (stored as a tag on the demoted version).

    Returns:
        Summary of the restored champion.

    Raises:
        RegistryStateError: If there is no previous champion to restore.
    """
    mlflow_cfg = config["mlflow"]
    client = _client(config)
    name = mlflow_cfg["registered_model_name"]
    previous = _alias_version(client, name, mlflow_cfg["previous_alias"])
    current = _alias_version(client, name, mlflow_cfg["champion_alias"])
    if previous is None:
        raise RegistryStateError(f"{name} has no @{mlflow_cfg['previous_alias']} to restore")
    client.set_registered_model_alias(name, mlflow_cfg["champion_alias"], previous)
    client.delete_registered_model_alias(name, mlflow_cfg["previous_alias"])
    if current:
        client.set_model_version_tag(name, current, "rolled_back_reason", reason)
    return _write_champion(client, config, name, previous, current, action="rollback")


def _write_champion(
    client: MlflowClient,
    config: dict[str, Any],
    name: str,
    version: str,
    replaced: str | None,
    action: str,
) -> dict[str, Any]:
    """Persist the current champion summary to ``reports/champion.json``."""
    model_version = client.get_model_version(name, version)
    summary = {
        "action": action,
        "registered_model_name": name,
        "version": int(version),
        "alias": config["mlflow"]["champion_alias"],
        "replaced_version": int(replaced) if replaced else None,
        "run_id": model_version.run_id,
        "model_uri": f"models:/{name}@{config['mlflow']['champion_alias']}",
        "tags": dict(model_version.tags),
    }
    out = Path(config["paths"]["reports_dir"]) / "champion.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2))
    logger.info("%s: %s@champion -> v%s (was v%s)", action, name, version, replaced)
    return summary


def export_challenger_figures(challenger: pd.Series, config: dict[str, Any]) -> list[Path]:
    """Copy the challenger's evaluation plots from MLflow into ``reports/figures``.

    Args:
        challenger: Row returned by :func:`select_challenger`.
        config: Pipeline configuration.

    Returns:
        Paths of copied figures.
    """
    mlflow.set_tracking_uri(config["mlflow"]["tracking_uri"])
    figures_dir = Path(config["paths"]["figures_dir"])
    figures_dir.mkdir(parents=True, exist_ok=True)
    local_dir = Path(
        mlflow.artifacts.download_artifacts(
            run_id=challenger["run_id"],
            artifact_path="evaluation",
            dst_path=str(figures_dir / ".tmp"),
        )
    )
    copied = []
    for png in sorted(local_dir.glob("*.png")):
        target = figures_dir / f"challenger_{png.name}"
        shutil.copyfile(png, target)
        copied.append(target)
    shutil.rmtree(figures_dir / ".tmp", ignore_errors=True)
    return copied


def register(table: pd.DataFrame, config: dict[str, Any]) -> dict[str, Any]:
    """Select, register and document the challenger for one pipeline execution.

    Args:
        table: Experiment table for the current pipeline run.
        config: Pipeline configuration.

    Returns:
        Challenger summary (also written to ``reports/challenger.json``); the gate
        outcome of every run is written to ``reports/gate_report.csv``.
    """
    reports_dir = Path(config["paths"]["reports_dir"])
    reports_dir.mkdir(parents=True, exist_ok=True)
    checks = gate_report(table, config)
    checks.insert(0, "run_name", table["run_name"])
    checks.to_csv(reports_dir / "gate_report.csv", index=False)

    challenger = select_challenger(table, config)
    summary = register_challenger(challenger, config)
    summary["figures"] = [p.name for p in export_challenger_figures(challenger, config)]
    (reports_dir / "challenger.json").write_text(json.dumps(summary, indent=2))
    return summary
