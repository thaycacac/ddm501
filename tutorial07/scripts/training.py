"""
============================================
TRAIN & REGISTER MODEL TO MLFLOW
============================================

This script:
1. Trains a simple model
2. Logs to MLFlow
3. Registers to MLFlow Model Registry
4. Promotes to Production stage

Run from the host:   python scripts/training.py
Reused by Airflow:   the model_retrain DAG imports train_and_register() / promote_to_production().
Endpoints default to localhost and can be overridden with environment variables.
"""

import os

import mlflow
import mlflow.sklearn
from sklearn.datasets import load_wine
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split

# ============================================
# CONFIGURATION
# ============================================

MLFLOW_TRACKING_URI = os.getenv('MLFLOW_TRACKING_URI', 'http://localhost:5000')
MODEL_NAME = os.getenv('MODEL_NAME', 'wine_quality_model')
EXPERIMENT_NAME = os.getenv('EXPERIMENT_NAME', 'wine_quality_experiment')

# Configure MinIO S3 for artifacts
os.environ.setdefault('MLFLOW_S3_ENDPOINT_URL', 'http://localhost:9000')
os.environ.setdefault('AWS_ACCESS_KEY_ID', 'minio')
os.environ.setdefault('AWS_SECRET_ACCESS_KEY', 'minio123')
os.environ.setdefault('MLFLOW_S3_IGNORE_TLS', 'true')

DEFAULT_PARAMS = {
    'n_estimators': 100,
    'max_depth': 10,
    'min_samples_split': 2,
    'random_state': 42
}


# ============================================
# TRAIN + REGISTER
# ============================================

def train_and_register(run_name: str = "RandomForest_v1", params: dict = None, tags: dict = None) -> dict:
    """Train on the wine dataset, log to MLflow and register a new model version.

    Returns run_id, registered version and metrics.
    """
    params = {**DEFAULT_PARAMS, **(params or {})}
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)

    wine = load_wine()
    X, y = wine.data, wine.target
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    with mlflow.start_run(run_name=run_name) as run:
        if tags:
            mlflow.set_tags(tags)

        model = RandomForestClassifier(**params)
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'f1_score': f1_score(y_test, y_pred, average='weighted'),
            'precision': precision_score(y_test, y_pred, average='weighted'),
            'recall': recall_score(y_test, y_pred, average='weighted'),
        }

        mlflow.log_params(params)
        mlflow.log_metrics(metrics)
        mlflow.sklearn.log_model(
            model,
            artifact_path="model",
            registered_model_name=MODEL_NAME,
            signature=mlflow.models.infer_signature(X_train, y_pred),
            input_example=X_train[:5]
        )
        run_id = run.info.run_id
        experiment_id = run.info.experiment_id

    client = mlflow.tracking.MlflowClient()
    versions = client.search_model_versions(f"name='{MODEL_NAME}' and run_id='{run_id}'")
    version = max(int(v.version) for v in versions) if versions else None

    return {
        'run_id': run_id,
        'experiment_id': experiment_id,
        'model_name': MODEL_NAME,
        'version': str(version) if version is not None else None,
        'metrics': metrics,
        'train_samples': len(X_train),
        'test_samples': len(X_test),
    }


# ============================================
# PROMOTE TO PRODUCTION
# ============================================

def promote_to_production(version: str) -> None:
    """Move ``version`` to Production and archive the previous Production version."""
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    client = mlflow.tracking.MlflowClient()
    client.transition_model_version_stage(
        name=MODEL_NAME,
        version=version,
        stage="Production",
        archive_existing_versions=True  # Archive old production versions
    )


def main():
    print(f"🔧 MLFlow Tracking URI: {MLFLOW_TRACKING_URI}")
    print(f"🎯 Experiment: {EXPERIMENT_NAME}")
    print("\n🎯 Training model...")

    result = train_and_register()
    metrics = result['metrics']

    print(f"   Training samples: {result['train_samples']}")
    print(f"   Test samples: {result['test_samples']}")
    print(f"\n📈 Model Performance:")
    print(f"   Accuracy:  {metrics['accuracy']:.4f}")
    print(f"   F1 Score:  {metrics['f1_score']:.4f}")
    print(f"   Precision: {metrics['precision']:.4f}")
    print(f"   Recall:    {metrics['recall']:.4f}")
    print(f"\n Model logged to MLFlow!")
    print(f"   Run ID: {result['run_id']}")

    print("\n Promoting model to Production stage...")
    if result['version']:
        promote_to_production(result['version'])
        print(f"✅ Model promoted to Production!")
        print(f"   Model: {MODEL_NAME}")
        print(f"   Version: {result['version']}")
        print(f"   Stage: Production")
    else:
        print("❌ No model versions found")

    print("\n" + "="*50)
    print(" SETUP COMPLETE!")
    print("="*50)
    print(f"\n Next steps:")
    print(f"   1. Start API: docker-compose up -d api")
    print(f"   2. Test API: curl http://localhost:8000/health")
    print(f"   3. Make prediction: curl -X POST http://localhost:8000/predict \\")
    print(f"      -H 'Content-Type: application/json' \\")
    print(f"      -d '{{\"features\": [13.2, 1.78, 2.14, 11.2, 100, 2.65, 2.76, 0.26, 1.28, 4.38, 1.05, 3.4, 1050]}}'")
    print(f"   4. View metrics: http://localhost:8000/metrics")
    print(f"   5. View Grafana: http://localhost:3000")
    print(f"   6. View MLFlow: http://localhost:5000")
    print()


if __name__ == "__main__":
    main()
