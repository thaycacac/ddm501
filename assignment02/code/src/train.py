"""Model construction and MLflow-tracked training for every configured experiment."""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

import mlflow
import numpy as np
import pandas as pd
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline
from lightgbm import LGBMClassifier
from mlflow.models import infer_signature
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_validate
from xgboost import XGBClassifier

from src.config import PROJECT_ROOT, set_global_seed
from src.data import TARGET_COLUMN, load_split
from src.evaluate import (
    compute_metrics,
    cost_optimal_threshold,
    plot_confusion,
    plot_feature_importance,
    plot_roc_pr,
)
from src.features import FeatureEngineer, build_preprocessor, raw_input_columns

logger = logging.getLogger(__name__)

MODEL_TYPES = ("logistic_regression", "random_forest", "xgboost", "lightgbm")
# Audit-only columns: never model inputs, used for fairness slices.
FAIRNESS_GROUPS = {"gender": "gender", "senior": "SeniorCitizen"}


def git_metadata(cwd: Path = PROJECT_ROOT) -> dict[str, str]:
    """Return the current git commit and dirty flag (``unknown`` outside git).

    Args:
        cwd: Directory inside the repository.

    Returns:
        Dict with ``git_sha`` and ``git_dirty``.
    """
    baked_sha = os.environ.get("TELCO_GIT_SHA")
    if baked_sha:  # set at image build time; containers ship without git
        return {"git_sha": baked_sha, "git_dirty": os.environ.get("TELCO_GIT_DIRTY", "unknown")}
    git = shutil.which("git")
    if git is None:
        return {"git_sha": "unknown", "git_dirty": "unknown"}

    def _git(*args: str) -> str:
        return subprocess.run(  # noqa: S603 - fixed git arguments, no user input
            [git, *args], cwd=cwd, capture_output=True, text=True, check=True
        ).stdout.strip()

    try:
        sha = _git("rev-parse", "HEAD")
        dirty = bool(_git("status", "--porcelain", "--", "."))
    except (OSError, subprocess.CalledProcessError):
        return {"git_sha": "unknown", "git_dirty": "unknown"}
    return {"git_sha": sha, "git_dirty": str(dirty).lower()}


def build_estimator(
    model: str, params: dict[str, Any], imbalance: str, y_train: pd.Series, seed: int
) -> Any:
    """Instantiate a classifier with deterministic settings.

    Args:
        model: One of :data:`MODEL_TYPES`.
        params: Hyperparameters from the experiment config.
        imbalance: ``none``, ``class_weight`` or ``smote``.
        y_train: Training labels (used for ``scale_pos_weight``).
        seed: Random seed.

    Returns:
        Unfitted estimator.

    Raises:
        ValueError: If ``model`` is unknown.
    """
    weighted = imbalance == "class_weight"
    if model == "logistic_regression":
        return LogisticRegression(
            **params, class_weight="balanced" if weighted else None, random_state=seed
        )
    if model == "random_forest":
        return RandomForestClassifier(
            **params,
            class_weight="balanced_subsample" if weighted else None,
            random_state=seed,
            n_jobs=4,
        )
    if model == "xgboost":
        pos = float(y_train.sum())
        return XGBClassifier(
            **params,
            scale_pos_weight=(len(y_train) - pos) / pos if weighted else 1.0,
            tree_method="hist",
            eval_metric="logloss",
            random_state=seed,
            n_jobs=4,
        )
    if model == "lightgbm":
        return LGBMClassifier(
            **params,
            class_weight="balanced" if weighted else None,
            random_state=seed,
            deterministic=True,
            force_row_wise=True,
            n_jobs=4,
            verbose=-1,
        )
    raise ValueError(f"Unknown model '{model}', expected one of {MODEL_TYPES}")


def build_pipeline(experiment: dict[str, Any], y_train: pd.Series, seed: int) -> Pipeline:
    """Assemble feature engineering, encoding, optional SMOTE and the classifier.

    Args:
        experiment: One entry of ``experiments`` in the config.
        y_train: Training labels.
        seed: Random seed.

    Returns:
        Unfitted imbalanced-learn pipeline (SMOTE is only applied during fit).
    """
    steps: list[tuple[str, Any]] = [
        ("features", FeatureEngineer(experiment["feature_set"])),
        ("preprocess", build_preprocessor(experiment["feature_set"])),
    ]
    if experiment["imbalance"] == "smote":
        steps.append(("smote", SMOTE(random_state=seed)))
    steps.append(
        (
            "model",
            build_estimator(
                experiment["model"],
                dict(experiment.get("params", {})),
                experiment["imbalance"],
                y_train,
                seed,
            ),
        )
    )
    return Pipeline(steps)


def _importances(pipeline: Pipeline) -> tuple[list[str], np.ndarray] | None:
    """Extract encoded feature names and importances/coefficients if available."""
    names = list(pipeline.named_steps["preprocess"].get_feature_names_out())
    model = pipeline.named_steps["model"]
    if hasattr(model, "feature_importances_"):
        return names, np.asarray(model.feature_importances_, dtype=float)
    if hasattr(model, "coef_"):
        return names, np.asarray(model.coef_[0], dtype=float)
    return None


def _split_xy(frame: pd.DataFrame, feature_set: str) -> tuple[pd.DataFrame, pd.Series]:
    """Split a processed frame into raw model inputs and the target.

    Integer inputs are cast to float so the logged model signature still accepts
    records with missing values at serving time.
    """
    features = frame[raw_input_columns(feature_set)].copy()
    int_cols = features.select_dtypes("integer").columns
    features[int_cols] = features[int_cols].astype("float64")
    return features, frame[TARGET_COLUMN]


def setup_mlflow(config: dict[str, Any]) -> str:
    """Point MLflow at the configured backend and ensure the experiment exists.

    Args:
        config: Pipeline configuration.

    Returns:
        Experiment ID.
    """
    mlflow_cfg = config["mlflow"]
    mlflow.set_tracking_uri(mlflow_cfg["tracking_uri"])
    experiment = mlflow.get_experiment_by_name(mlflow_cfg["experiment_name"])
    if experiment is None:
        artifact_root = mlflow_cfg.get("artifact_root")
        location = None
        if artifact_root:
            location = artifact_root if "://" in artifact_root else Path(artifact_root).as_uri()
        experiment_id = mlflow.create_experiment(
            mlflow_cfg["experiment_name"],
            artifact_location=location,
            tags={"project": config["project"]["name"], "task": "binary-classification"},
        )
    else:
        experiment_id = experiment.experiment_id
    mlflow.set_experiment(experiment_id=experiment_id)
    return experiment_id


def run_experiment(
    experiment: dict[str, Any],
    data: dict[str, pd.DataFrame],
    config: dict[str, Any],
    common_tags: dict[str, str],
) -> str:
    """Train, evaluate and log one experiment configuration as an MLflow run.

    Args:
        experiment: One entry of ``experiments`` in the config.
        data: Processed ``train``/``val``/``test`` frames.
        config: Pipeline configuration.
        common_tags: Lineage tags shared by every run of this pipeline execution.

    Returns:
        MLflow run ID.
    """
    seed = int(config["project"]["seed"])
    set_global_seed(seed)
    feature_set = experiment["feature_set"]
    eligible = bool(experiment.get("eligible", True))
    x_train, y_train = _split_xy(data["train"], feature_set)
    x_val, y_val = _split_xy(data["val"], feature_set)
    x_test, y_test = _split_xy(data["test"], feature_set)

    pipeline = build_pipeline(experiment, y_train, seed)
    cv = StratifiedKFold(n_splits=config["training"]["cv_folds"], shuffle=True, random_state=seed)

    with mlflow.start_run(run_name=experiment["name"]) as run:
        mlflow.set_tags(
            {
                **common_tags,
                "experiment_config": experiment["name"],
                "is_baseline": str(
                    experiment["name"] == config["selection"]["baseline_experiment"]
                ).lower(),
                "eligible_for_selection": str(eligible).lower(),
                "mlflow.note.content": (
                    f"{experiment['model']} | features={experiment['feature_set']} | "
                    f"imbalance={experiment['imbalance']} | threshold={experiment['threshold']}"
                ),
            }
        )
        mlflow.log_params(
            {
                "model": experiment["model"],
                "feature_set": experiment["feature_set"],
                "imbalance": experiment["imbalance"],
                "threshold_strategy": experiment["threshold"],
                "eligible": str(eligible).lower(),
                "seed": seed,
                "cv_folds": config["training"]["cv_folds"],
                "n_train": len(x_train),
                "n_val": len(x_val),
                "n_test": len(x_test),
                **{f"model__{k}": v for k, v in experiment.get("params", {}).items()},
            }
        )

        cv_scores = cross_validate(
            pipeline, x_train, y_train, cv=cv, scoring=["roc_auc", "average_precision"]
        )
        start = time.perf_counter()
        pipeline.fit(x_train, y_train)
        train_seconds = time.perf_counter() - start

        val_score = pipeline.predict_proba(x_val)[:, 1]
        start = time.perf_counter()
        test_score = pipeline.predict_proba(x_test)[:, 1]
        latency_ms_per_1k = (time.perf_counter() - start) / len(x_test) * 1e6

        if experiment["threshold"] == "cost_optimal":
            threshold = cost_optimal_threshold(
                y_val.to_numpy(),
                val_score,
                config["business"],
                max_contact_rate=config["business"].get("max_contact_rate"),
            )
        else:
            threshold = float(
                experiment.get("threshold_value", config["training"]["default_threshold"])
            )
        mlflow.log_param("threshold", threshold)

        metrics: dict[str, float] = {
            "cv_roc_auc_mean": float(np.mean(cv_scores["test_roc_auc"])),
            "cv_roc_auc_std": float(np.std(cv_scores["test_roc_auc"])),
            "cv_pr_auc_mean": float(np.mean(cv_scores["test_average_precision"])),
            "train_seconds": train_seconds,
            "inference_ms_per_1k_rows": latency_ms_per_1k,
        }
        for prefix, split_name, y_true, y_score in (
            ("val", "val", y_val, val_score),
            ("test", "test", y_test, test_score),
        ):
            groups = {
                name: data[split_name][column].astype(str).to_numpy()
                for name, column in FAIRNESS_GROUPS.items()
            }
            split_metrics = compute_metrics(
                y_true.to_numpy(), y_score, threshold, config, groups=groups
            )
            metrics.update({f"{prefix}_{k}": v for k, v in split_metrics.items()})
        mlflow.log_metrics(metrics)

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            title = experiment["name"]
            plot_confusion(
                y_test.to_numpy(),
                test_score,
                threshold,
                tmp_dir / "confusion_matrix_test.png",
                f"{title} (test)",
            )
            plot_roc_pr(y_test.to_numpy(), test_score, tmp_dir / "roc_pr_test.png", title)
            importances = _importances(pipeline)
            if importances is not None:
                plot_feature_importance(
                    *importances, tmp_dir / "feature_importance.png", f"{title}: top features"
                )
            (tmp_dir / "experiment_config.json").write_text(json.dumps(experiment, indent=2))
            mlflow.log_artifacts(str(tmp_dir), artifact_path="evaluation")

        signature = infer_signature(x_val, pipeline.predict_proba(x_val))
        # skops (MLflow default) rejects the custom FeatureEngineer/imblearn types;
        # artifacts are produced and consumed only inside our own registry.
        model_info = mlflow.sklearn.log_model(
            pipeline,
            name="model",
            signature=signature,
            input_example=x_val.head(5),
            code_paths=[str(PROJECT_ROOT / "src")],
            serialization_format="cloudpickle",
            pyfunc_predict_fn="predict_proba",
        )
        mlflow.set_tag("model_uri", model_info.model_uri)
        logger.info(
            "%-24s val_pr_auc=%.4f val_cost=%.2f thr=%.2f",
            experiment["name"],
            metrics["val_pr_auc"],
            metrics["val_business_cost_per_customer"],
            threshold,
        )
        return run.info.run_id


def train_all(
    config: dict[str, Any],
    pipeline_run_id: str,
    data_manifest: dict[str, Any],
    only: list[str] | None = None,
) -> list[str]:
    """Run every configured experiment (or a subset) and log them to MLflow.

    Args:
        config: Pipeline configuration.
        pipeline_run_id: Identifier grouping all runs of this execution.
        data_manifest: Output of :func:`src.data.ingest` (for lineage tags).
        only: Optional list of experiment names to run.

    Returns:
        MLflow run IDs in execution order.
    """
    processed_dir = config["paths"]["processed_dir"]
    data = {name: load_split(processed_dir, name) for name in ("train", "val", "test")}
    setup_mlflow(config)
    common_tags = {
        "pipeline_run_id": pipeline_run_id,
        "data_sha256": data_manifest["sha256"],
        "data_rows": str(data_manifest["n_rows"]),
        "seed": str(config["project"]["seed"]),
        **git_metadata(),
    }
    experiments = [e for e in config["experiments"] if not only or e["name"] in only]
    return [run_experiment(exp, data, config, common_tags) for exp in experiments]
