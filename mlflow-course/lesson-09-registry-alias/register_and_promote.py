"""
BÀI 09 — Model Registry (tinh thần Tutorial 02 step3).

Tracking  = "đã thử gì?"
Registry  = "cái nào đang deploy / rollback về đâu?"

| Khái niệm          | Nghĩa                                      |
|--------------------|--------------------------------------------|
| Registered model   | Tên (vd: lesson-09-classifier), không phải file |
| Version            | Số append-only: 1, 2, 3… — register không ghi đè |
| Alias              | Con trỏ di chuyển (champion / challenger)  |

MLflow 2.x + Lab 2 dùng ALIAS, không dùng Staging/Production stages cũ.
Serving code nên gọi: models:/NAME@champion  — không hard-code version.
Promote = đổi alias (metadata), không copy file model.
"""
from __future__ import annotations

import os

import mlflow
from mlflow import MlflowClient
from sklearn.datasets import load_breast_cancer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5001")
EXPERIMENT = "mlflow-course-09"
MODEL_NAME = "lesson-09-classifier"


def train_and_log(C: float, run_name: str) -> str:
    X, y = load_breast_cancer(as_frame=True, return_X_y=True)
    X_tr, X_te, y_tr, _ = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )
    model = make_pipeline(
        StandardScaler(),
        LogisticRegression(C=C, max_iter=5000, random_state=0),
    )
    model.fit(X_tr, y_tr)
    with mlflow.start_run(run_name=run_name) as run:
        mlflow.log_param("C", C)
        mlflow.sklearn.log_model(model, "model", input_example=X_te.head(2))
        return run.info.run_id


def show(client: MlflowClient) -> None:
    # aliases nằm trên registered model: {alias: version}
    alias_of: dict[str, list[str]] = {}
    for alias, version in client.get_registered_model(MODEL_NAME).aliases.items():
        alias_of.setdefault(str(version), []).append(alias)

    print(f"\n{'version':>8}  {'aliases':<24} description")
    for mv in sorted(
        client.search_model_versions(f"name='{MODEL_NAME}'"),
        key=lambda m: int(m.version),
    ):
        aliases = ", ".join(sorted(alias_of.get(str(mv.version), []))) or "-"
        print(f"{mv.version:>8}  {aliases:<24} {mv.description}")


def main() -> None:
    mlflow.set_tracking_uri(TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT)
    client = MlflowClient()

    # Hai run → hai version (append-only)
    r1 = train_and_log(1.0, "candidate-C-1.0")
    r2 = train_and_log(0.1, "candidate-C-0.1")

    v1 = mlflow.register_model(f"runs:/{r1}/model", MODEL_NAME)
    client.update_model_version(MODEL_NAME, v1.version, description="C=1.0")
    v2 = mlflow.register_model(f"runs:/{r2}/model", MODEL_NAME)
    client.update_model_version(MODEL_NAME, v2.version, description="C=0.1")

    print(f"registered v{v1.version} from {r1}")
    print(f"registered v{v2.version} from {r2}")

    # Gán alias
    client.set_registered_model_alias(MODEL_NAME, "champion", str(v1.version))
    client.set_registered_model_alias(MODEL_NAME, "challenger", str(v2.version))
    print("\nAfter assign aliases:")
    show(client)

    # Promote: challenger → champion (chỉ metadata)
    print("\nPromote challenger → champion...")
    client.set_registered_model_alias(MODEL_NAME, "champion", str(v2.version))
    client.delete_registered_model_alias(MODEL_NAME, "challenger")
    print("After promote:")
    show(client)

    print(f"\nUI → Models → {MODEL_NAME}")
    print("Serving sẽ dùng: models:/{MODEL_NAME}@champion")


if __name__ == "__main__":
    main()
