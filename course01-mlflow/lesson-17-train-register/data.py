"""
BÀI 17 — data.py = tutorial02-extend/utils/data.py (gọn lại, cùng hành vi).

load_breast_cancer() mặc định trả NUMPY array (không có tên cột).
→ Signature của model sẽ là tensor (-1, 30) thay vì 30 cột có tên.
  (Bài 14 cũ dùng as_frame=True nên signature có tên cột — cả hai đều hợp lệ.)

Thứ tự trả về: X_train, X_test, y_train, y_test — nhớ kỹ, bài 19 sẽ gặp một
chỗ trong 04_loading_models.py lấy nhầm vị trí.
"""
from __future__ import annotations

from sklearn.datasets import load_breast_cancer
from sklearn.model_selection import train_test_split


def get_data(test_size: float = 0.2, random_state: int = 42):
    X, y = load_breast_cancer(return_X_y=True)
    # stratify=y: tỉ lệ lành/ác trong train và test giống nhau
    return train_test_split(X, y, test_size=test_size,
                            random_state=random_state, stratify=y)
