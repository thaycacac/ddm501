"""Shared setup. Imported by every step, not run on its own."""
import os

import mlflow

TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000")
EXPERIMENT = "breast-cancer-diagnosis"
MODEL_NAME = "breast-cancer-classifier"


def connect() -> None:
    """Point this process at the tracking server and the right experiment.

    Two calls, and they do different things. set_tracking_uri says WHERE runs
    are stored; set_experiment says WHICH drawer inside it they go into. Forget
    the first and everything lands in a local ./mlruns folder that the UI you
    have open is not reading -- the single most common "MLflow lost my run".
    """
    mlflow.set_tracking_uri(TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT)
