"""
Train a model and register it.

Tutorial 02 logged runs. This registers the result: the model gets a name, a
version number, and a home the API can fetch it from.

Run it twice and you get version 1 and version 2 -- registering never
overwrites.

    docker compose run --rm trainer python scripts/train_and_register.py
"""
import os

import mlflow
import mlflow.sklearn
from sklearn.datasets import load_breast_cancer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

EXPERIMENT = "breast-cancer-serving"
MODEL_NAME = os.getenv("MODEL_NAME", "breast-cancer-classifier")
N_TREES = int(os.getenv("N_TREES", "200"))


def main() -> None:
    mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])
    mlflow.set_experiment(EXPERIMENT)

    data = load_breast_cancer(as_frame=True)
    X, y = data.data, data.target          # 0 = malignant, 1 = benign
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    with mlflow.start_run() as run:
        model = make_pipeline(
            StandardScaler(),
            RandomForestClassifier(n_estimators=N_TREES, random_state=42),
        )
        model.fit(X_train, y_train)
        auc = roc_auc_score(y_test, model.predict_proba(X_test)[:, 1])

        mlflow.log_param("n_estimators", N_TREES)
        mlflow.log_metric("test_roc_auc", auc)

        # registered_model_name is what turns a logged model into a version in
        # the registry. The input example travels with it, so the API knows the
        # column order without being told.
        mlflow.sklearn.log_model(
            model,
            artifact_path="model",
            registered_model_name=MODEL_NAME,
            input_example=X_train.head(1),
        )
        print(f"run {run.info.run_id}  n_estimators={N_TREES}  roc_auc={auc:.4f}")

    latest = mlflow.MlflowClient().get_registered_model(MODEL_NAME).latest_versions
    version = max(int(v.version) for v in latest)
    print(f"registered {MODEL_NAME} version {version}")
    print(f"to serve it, set MODEL_VERSION={version} in .env and restart the API")


if __name__ == "__main__":
    main()
