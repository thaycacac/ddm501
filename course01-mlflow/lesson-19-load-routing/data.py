"""
BÀI 19 — data.py = tutorial02-extend/utils/data.py (giống bài 17).

Thứ tự trả về: X_train, X_test, y_train, y_test
"""
from __future__ import annotations

from sklearn.datasets import load_breast_cancer
from sklearn.model_selection import train_test_split


def get_data(test_size: float = 0.2, random_state: int = 42):
    X, y = load_breast_cancer(return_X_y=True)
    return train_test_split(X, y, test_size=test_size,
                            random_state=random_state, stratify=y)
