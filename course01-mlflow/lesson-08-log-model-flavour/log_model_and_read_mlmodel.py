"""
BÀI 08 — log_model: không chỉ pickle, mà kèm "flavour" metadata.

Flavour (sklearn / pytorch / ...) = cách MLflow hiểu và load lại model.
Mỗi model artifact có file MLmodel (YAML) mô tả:
  - flavors.sklearn.sklearn_version  ← version lúc pickle (T02 step4 hỏi cái này)
  - python_function (pyfunc)         ← interface chung để load/predict
  - signature / saved_input_example  ← nếu bạn truyền input_example

Tutorial 02: mlflow.sklearn.log_model(..., input_example=X_te.head(2))
"""
from __future__ import annotations

import os
from pathlib import Path

import mlflow
import sklearn
import yaml
from sklearn.datasets import load_breast_cancer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5001")
EXPERIMENT = "mlflow-course-08"


def main() -> None:
    mlflow.set_tracking_uri(TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT)

    X, y = load_breast_cancer(as_frame=True, return_X_y=True)
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )
    model = make_pipeline(
        StandardScaler(),
        LogisticRegression(C=1.0, max_iter=5000, random_state=0),
    )
    model.fit(X_tr, y_tr)

    with mlflow.start_run(run_name="log-model-with-flavour") as run:
        mlflow.log_param("sklearn_running", sklearn.__version__)

        # input_example → MLflow suy ra signature + lưu example (bớt warning)
        mlflow.sklearn.log_model(
            model,
            artifact_path="model",
            input_example=X_te.head(2),
        )
        run_id = run.info.run_id
        print(f"run_id = {run_id}")
        print(f"URI    = runs:/{run_id}/model")
        print(f"running sklearn = {sklearn.__version__}")

    # Tải artifact về local và đọc MLmodel (giống tinh thần T02 step4)
    local = Path(mlflow.artifacts.download_artifacts(f"runs:/{run_id}/model"))
    meta = yaml.safe_load((local / "MLmodel").read_text(encoding="utf-8"))
    print("\n--- MLmodel (rút gọn) ---")
    print("flavors:", list(meta.get("flavors", {}).keys()))
    sk = meta["flavors"]["sklearn"]
    print("sklearn_version pickled:", sk.get("sklearn_version"))
    print("MLmodel path:", local / "MLmodel")
    print("\nUI → run → Artifacts → model/ → mở file MLmodel")


if __name__ == "__main__":
    main()
