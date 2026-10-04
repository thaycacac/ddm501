"""Configuration loading with environment-variable overrides.

The YAML file is the single source of truth for defaults. Any nested key can be
overridden at runtime with ``TELCO__<SECTION>__<KEY>=<yaml value>`` so the same
image runs unchanged on a laptop, in Docker, or inside an Airflow worker.
"""

from __future__ import annotations

import copy
import os
import random
from pathlib import Path
from typing import Any

import numpy as np
import yaml

ENV_PREFIX = "TELCO__"
PROJECT_ROOT = Path(os.environ.get("TELCO_PROJECT_ROOT", Path(__file__).resolve().parents[1]))
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "configs" / "config.yaml"


def _set_nested(config: dict[str, Any], keys: list[str], value: Any) -> None:
    """Set ``config[k1][k2]...[kn] = value``, creating intermediate dicts."""
    node = config
    for key in keys[:-1]:
        node = node.setdefault(key, {})
    node[keys[-1]] = value


def apply_env_overrides(
    config: dict[str, Any], environ: dict[str, str] | None = None
) -> dict[str, Any]:
    """Return a copy of ``config`` with ``TELCO__A__B`` variables applied.

    Args:
        config: Parsed YAML configuration.
        environ: Environment mapping; defaults to ``os.environ``.

    Returns:
        A new configuration dict including the overrides.
    """
    environ = dict(os.environ) if environ is None else environ
    result = copy.deepcopy(config)
    for name, raw_value in sorted(environ.items()):
        if not name.startswith(ENV_PREFIX):
            continue
        keys = [part.lower() for part in name[len(ENV_PREFIX) :].split("__") if part]
        if keys:
            _set_nested(result, keys, yaml.safe_load(raw_value))
    return result


def _resolve_paths(config: dict[str, Any], root: Path) -> dict[str, Any]:
    """Make relative paths and sqlite URIs absolute with respect to ``root``."""
    for key, value in config.get("paths", {}).items():
        path = Path(value)
        config["paths"][key] = str(path if path.is_absolute() else root / path)

    mlflow_cfg = config.get("mlflow", {})
    uri = str(mlflow_cfg.get("tracking_uri", ""))
    prefix = "sqlite:///"
    if uri.startswith(prefix) and not uri.startswith(prefix + "/"):
        mlflow_cfg["tracking_uri"] = f"{prefix}{root / uri[len(prefix):]}"
    artifact_root = mlflow_cfg.get("artifact_root")
    if artifact_root and "://" not in str(artifact_root):
        path = Path(artifact_root)
        mlflow_cfg["artifact_root"] = str(path if path.is_absolute() else root / path)
    return config


def load_config(
    path: str | Path | None = None, environ: dict[str, str] | None = None
) -> dict[str, Any]:
    """Load the pipeline configuration.

    Args:
        path: YAML file to read. Defaults to ``$TELCO_CONFIG`` or
            ``configs/config.yaml`` in the project root.
        environ: Environment mapping used for overrides (testing hook).

    Returns:
        Configuration dict with overrides applied and paths resolved.
    """
    environ = dict(os.environ) if environ is None else environ
    config_path = Path(path or environ.get("TELCO_CONFIG", DEFAULT_CONFIG_PATH))
    with config_path.open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    config = apply_env_overrides(config, environ)
    return _resolve_paths(config, PROJECT_ROOT)


def set_global_seed(seed: int) -> None:
    """Seed every random number generator used by the pipeline.

    Args:
        seed: Seed value from ``project.seed``.
    """
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
