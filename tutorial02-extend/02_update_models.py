"""
    This script is to demonstrate how to update the model version and tags.
    We will use the mlflow client to update the model version and tags.
"""
import os
from dotenv import load_dotenv
from mlflow.tracking import MlflowClient

load_dotenv(dotenv_path=".env")

print(f"MLFLOW_TRACKING_URI: {os.environ['MLFLOW_TRACKING_URI']}")
# initialize the mlflow client
client = MlflowClient(tracking_uri=os.environ['MLFLOW_TRACKING_URI'])

# update the model version and tags
MODEL_NAME = "breast_cancer-predictor"
# 01_training.py registers versions 1 then 2 — update the newer one.
version = "2"
description = """
This model is trained on the breast cancer dataset (Wisconsin Diagnostic).
Model information:
- Algorithm: Random Forest
- n_estimators: 500
- Random state: 42
- Dataset: breast_cancer
"""
client.update_model_version(
    name=MODEL_NAME,
    version=version,
    description=description,
)

client.set_model_version_tag(
    name=MODEL_NAME,
    version=version,
    key='algorithm',
    value='random_forest',
)