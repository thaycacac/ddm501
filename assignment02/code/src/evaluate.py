"""Metrics, business cost, threshold tuning, plots and MLflow result export."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.metrics import (  # noqa: E402
    ConfusionMatrixDisplay,
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)

logger = logging.getLogger(__name__)

THRESHOLD_GRID = np.round(np.arange(0.05, 0.951, 0.01), 2)


def business_cost(
    y_true: np.ndarray, y_pred: np.ndarray, business: dict[str, float]
) -> dict[str, float]:
    """Expected campaign cost under the configured business assumptions.

    Args:
        y_true: Binary ground truth.
        y_pred: Binary decisions (1 = contact with retention offer).
        business: ``business`` config section.

    Returns:
        Total cost, cost per customer and net savings versus no campaign
        (no campaign = every churner is lost).
    """
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    loss, offer, success = (
        business["churn_loss"],
        business["offer_cost"],
        business["offer_success_rate"],
    )
    total = tp * (offer + (1.0 - success) * loss) + fp * offer + fn * loss
    no_campaign = (tp + fn) * loss
    n = len(y_true)
    return {
        "business_cost": float(total),
        "business_cost_per_customer": float(total / n),
        "net_savings_per_1k": float((no_campaign - total) / n * 1000.0),
    }


def top_k_metrics(y_true: np.ndarray, y_score: np.ndarray, fraction: float) -> dict[str, float]:
    """Lift and recall when contacting only the top ``fraction`` riskiest customers.

    Args:
        y_true: Binary ground truth.
        y_score: Predicted churn probabilities.
        fraction: Share of customers the retention team can contact.

    Returns:
        ``lift_at_top_k``, ``precision_at_top_k`` and ``recall_at_top_k``.
    """
    y_true = np.asarray(y_true)
    k = max(1, int(round(len(y_true) * fraction)))
    order = np.argsort(-np.asarray(y_score), kind="mergesort")[:k]
    hits = y_true[order].sum()
    precision_k = hits / k
    base_rate = y_true.mean()
    return {
        "lift_at_top_k": float(precision_k / base_rate) if base_rate else 0.0,
        "precision_at_top_k": float(precision_k),
        "recall_at_top_k": float(hits / y_true.sum()) if y_true.sum() else 0.0,
    }


def recall_gap(
    y_true: np.ndarray, y_pred: np.ndarray, groups: np.ndarray, z: float = 1.645
) -> tuple[float, float]:
    """Equal-opportunity gap: largest recall difference between groups.

    Args:
        y_true: Binary ground truth.
        y_pred: Binary decisions.
        groups: Group label per row (e.g. gender).
        z: Normal quantile for the one-sided lower confidence bound (1.645 = 95%).

    Returns:
        ``(gap, lower_bound)`` where ``gap = max(recall_g) - min(recall_g)`` over groups
        with positives and ``lower_bound`` subtracts ``z`` standard errors of the
        difference of two proportions (clipped at 0).
    """
    y_true, y_pred, groups = map(np.asarray, (y_true, y_pred, groups))
    stats = []
    for g in np.unique(groups):
        positives = y_true[groups == g] == 1
        if positives.sum() > 0:
            hits = y_pred[groups == g][positives]
            stats.append((float(hits.mean()), int(positives.sum())))
    if len(stats) < 2:
        return 0.0, 0.0
    (r_hi, n_hi), (r_lo, n_lo) = max(stats), min(stats)
    std_err = np.sqrt(r_hi * (1 - r_hi) / n_hi + r_lo * (1 - r_lo) / n_lo)
    gap = r_hi - r_lo
    return float(gap), float(max(0.0, gap - z * std_err))


def compute_metrics(
    y_true: np.ndarray,
    y_score: np.ndarray,
    threshold: float,
    config: dict[str, Any],
    groups: dict[str, np.ndarray] | None = None,
) -> dict[str, float]:
    """All model, business and fairness metrics for one split.

    Args:
        y_true: Binary ground truth.
        y_score: Predicted churn probabilities.
        threshold: Decision threshold.
        config: Pipeline configuration.
        groups: Optional ``{name: group labels}``; adds ``<name>_recall_gap`` and its
            95% lower confidence bound ``<name>_recall_gap_lcb`` per entry.

    Returns:
        Flat metric dict (unprefixed).
    """
    y_pred = (y_score >= threshold).astype(int)
    metrics = {
        "roc_auc": roc_auc_score(y_true, y_score),
        "pr_auc": average_precision_score(y_true, y_score),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "accuracy": accuracy_score(y_true, y_pred),
        "brier": brier_score_loss(y_true, y_score),
        "contact_rate": float(y_pred.mean()),
    }
    metrics.update(business_cost(y_true, y_pred, config["business"]))
    metrics.update(top_k_metrics(y_true, y_score, config["business"]["top_k_fraction"]))
    for name, labels in (groups or {}).items():
        gap, lower_bound = recall_gap(y_true, y_pred, labels)
        metrics[f"{name}_recall_gap"] = gap
        metrics[f"{name}_recall_gap_lcb"] = lower_bound
    return {key: float(value) for key, value in metrics.items()}


def cost_optimal_threshold(
    y_true: np.ndarray,
    y_score: np.ndarray,
    business: dict[str, float],
    max_contact_rate: float | None = None,
) -> float:
    """Pick the threshold minimising expected business cost on a validation set.

    Args:
        y_true: Validation ground truth.
        y_score: Validation probabilities.
        business: ``business`` config section.
        max_contact_rate: Optional capacity limit; thresholds that would contact a
            larger share of customers are not considered.

    Returns:
        Best feasible threshold from :data:`THRESHOLD_GRID` (lowest on ties). If no
        threshold is feasible, the highest grid value.
    """
    best_threshold, best_cost = float(THRESHOLD_GRID[-1]), np.inf
    for t in THRESHOLD_GRID:
        y_pred = (y_score >= t).astype(int)
        if max_contact_rate is not None and y_pred.mean() > max_contact_rate:
            continue
        cost = business_cost(y_true, y_pred, business)["business_cost"]
        if cost < best_cost:
            best_threshold, best_cost = float(t), cost
    return best_threshold


def plot_confusion(
    y_true: np.ndarray, y_score: np.ndarray, threshold: float, path: Path, title: str
) -> Path:
    """Save a confusion-matrix figure.

    Args:
        y_true: Ground truth.
        y_score: Probabilities.
        threshold: Decision threshold.
        path: Output PNG path.
        title: Figure title.

    Returns:
        ``path``.
    """
    fig, ax = plt.subplots(figsize=(4.5, 4))
    ConfusionMatrixDisplay.from_predictions(
        y_true,
        (y_score >= threshold).astype(int),
        display_labels=["Stay", "Churn"],
        cmap="Blues",
        ax=ax,
        colorbar=False,
    )
    ax.set_title(f"{title}\nthreshold={threshold:.2f}")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_roc_pr(y_true: np.ndarray, y_score: np.ndarray, path: Path, title: str) -> Path:
    """Save side-by-side ROC and precision-recall curves.

    Args:
        y_true: Ground truth.
        y_score: Probabilities.
        path: Output PNG path.
        title: Figure title.

    Returns:
        ``path``.
    """
    fpr, tpr, _ = roc_curve(y_true, y_score)
    precision, recall, _ = precision_recall_curve(y_true, y_score)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    ax1.plot(fpr, tpr, label=f"ROC-AUC={roc_auc_score(y_true, y_score):.3f}")
    ax1.plot([0, 1], [0, 1], "--", color="grey")
    ax1.set(xlabel="False positive rate", ylabel="True positive rate", title="ROC curve")
    ax1.legend(loc="lower right")
    ax2.plot(recall, precision, label=f"PR-AUC={average_precision_score(y_true, y_score):.3f}")
    ax2.axhline(np.mean(y_true), ls="--", color="grey", label="Base rate")
    ax2.set(xlabel="Recall", ylabel="Precision", title="Precision-recall curve")
    ax2.legend(loc="upper right")
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_feature_importance(names: list[str], values: np.ndarray, path: Path, title: str) -> Path:
    """Save a horizontal bar chart of the top-15 absolute importances.

    Args:
        names: Feature names after encoding.
        values: Importances or coefficients (same order as ``names``).
        path: Output PNG path.
        title: Figure title.

    Returns:
        ``path``.
    """
    series = pd.Series(np.abs(values), index=names).sort_values().tail(15)
    fig, ax = plt.subplots(figsize=(7, 5))
    series.plot.barh(ax=ax, color="#2b6cb0")
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def export_runs(config: dict[str, Any], pipeline_run_id: str) -> pd.DataFrame:
    """Export every MLflow run of one pipeline execution to ``reports/experiments.csv``.

    Args:
        config: Pipeline configuration.
        pipeline_run_id: Value of the ``pipeline_run_id`` tag to filter on.

    Returns:
        Exported dataframe (one row per run, sorted by the selection metric).
    """
    import mlflow

    mlflow.set_tracking_uri(config["mlflow"]["tracking_uri"])
    runs = mlflow.search_runs(
        experiment_names=[config["mlflow"]["experiment_name"]],
        filter_string=f"tags.pipeline_run_id = '{pipeline_run_id}'",
        output_format="pandas",
    )
    if runs.empty:
        raise RuntimeError(f"No MLflow runs found for pipeline_run_id={pipeline_run_id}")

    keep = ["run_id", "tags.mlflow.runName", "tags.pipeline_run_id", "tags.data_sha256"]
    keep += [
        "tags.git_sha",
        "tags.git_dirty",
        "params.seed",
        "params.model",
        "params.feature_set",
        "params.imbalance",
        "params.threshold_strategy",
        "params.threshold",
        "params.eligible",
    ]
    keep += sorted(c for c in runs.columns if c.startswith("params.model__"))
    metric_cols = sorted(c for c in runs.columns if c.startswith("metrics."))
    table = runs[[c for c in keep if c in runs.columns] + metric_cols].copy()
    table.columns = [c.split(".", 1)[1] if "." in c else c for c in table.columns]
    table = table.rename(columns={"mlflow.runName": "run_name"})
    selection = config["selection"]
    table = table.sort_values(
        [selection["metric"], selection["tie_breaker"]],
        ascending=[selection["mode"] == "min", False],
    ).reset_index(drop=True)
    metric_names = [c.split(".", 1)[1] for c in metric_cols]
    table[metric_names] = table[metric_names].round(4)

    reports_dir = Path(config["paths"]["reports_dir"])
    reports_dir.mkdir(parents=True, exist_ok=True)
    table.to_csv(reports_dir / "experiments.csv", index=False)
    logger.info("Exported %d runs to %s", len(table), reports_dir / "experiments.csv")
    return table


def plot_run_comparison(table: pd.DataFrame, figures_dir: Path) -> list[Path]:
    """Create cross-run comparison charts from the exported experiment table.

    Args:
        table: Output of :func:`export_runs`.
        figures_dir: Directory for PNG files.

    Returns:
        Paths of the generated figures.
    """
    figures_dir.mkdir(parents=True, exist_ok=True)
    ordered = table.sort_values("val_pr_auc")
    fig, ax = plt.subplots(figsize=(9, 6))
    y = np.arange(len(ordered))
    ax.barh(y - 0.2, ordered["val_roc_auc"], height=0.4, label="ROC-AUC (val)")
    ax.barh(y + 0.2, ordered["val_pr_auc"], height=0.4, label="PR-AUC (val)")
    ax.set_yticks(y, ordered["run_name"])
    ax.set_xlim(0.5, 0.9)
    ax.set_xlabel("Score")
    ax.set_title("Ranking quality per experiment (validation split)")
    ax.legend(loc="lower right")
    fig.tight_layout()
    metric_path = figures_dir / "runs_ranking_metrics.png"
    fig.savefig(metric_path, dpi=150)
    plt.close(fig)

    ordered = table.sort_values("val_business_cost_per_customer", ascending=False)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 6), sharey=True)
    y = np.arange(len(ordered))
    cost = ordered["val_business_cost_per_customer"]
    no_campaign = float((cost + ordered["val_net_savings_per_1k"] / 1000.0).iloc[0])
    ax1.barh(y, cost, color="#c05621")
    for pos, value in zip(y, cost, strict=True):
        ax1.text(value + 0.1, pos, f"{value:.2f}", va="center", fontsize=8)
    ax1.axvline(no_campaign, ls="--", color="grey", label=f"No campaign (${no_campaign:.2f})")
    ax1.set_xlim(cost.min() - 3, no_campaign + 1.5)
    ax1.set_yticks(y, ordered["run_name"])
    ax1.set_xlabel("Expected cost per customer ($, lower is better; axis zoomed)")
    ax1.set_title("Business cost (validation)")
    ax1.legend(loc="lower right")
    ax2.barh(y - 0.2, ordered["val_recall"], height=0.4, label="Recall")
    ax2.barh(y + 0.2, ordered["val_precision"], height=0.4, label="Precision")
    ax2.set_xlabel("Score at the run's decision threshold")
    ax2.set_title("Recall vs precision (validation)")
    ax2.legend(loc="lower right")
    fig.tight_layout()
    cost_path = figures_dir / "runs_business_cost.png"
    fig.savefig(cost_path, dpi=150)
    plt.close(fig)
    return [metric_path, cost_path]
