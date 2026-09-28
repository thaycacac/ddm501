"""Print one real row as a /predict body. Typing thirty numbers is not the lesson."""
import json

from sklearn.datasets import load_breast_cancer
from sklearn.model_selection import train_test_split

data = load_breast_cancer(as_frame=True)
_, X_test, _, y_test = train_test_split(
    data.data, data.target, test_size=0.2, stratify=data.target, random_state=42
)
print(json.dumps({"features": [float(v) for v in X_test.iloc[0]]}))
# This row is malignant. The API should agree.
