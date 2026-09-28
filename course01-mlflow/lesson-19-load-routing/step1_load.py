"""
BÀI 19 — Bước 1: tutorial02-extend/04_loading_models.py, viết lại có comment.

Load cùng một model bằng 2 cách (alias @dev và version /2), predict trên X_test,
đo accuracy. Cuối cùng chỉ ra chỗ extend lấy nhầm biến.
"""
from __future__ import annotations

import mlflow
import mlflow.pyfunc
from mlflow import MlflowClient
from sklearn.metrics import accuracy_score

from connect import MODEL_NAME, connect
from data import get_data

ALIAS = "dev"
VERSION = "2"


def load_and_score(model_uri: str, X_test, y_test) -> None:
    # load_model: models:/... → hỏi registry ra run_id → tải thư mục model/ từ MinIO
    #             vào thư mục tạm → đọc MLmodel → dựng model theo flavour
    model = mlflow.pyfunc.load_model(model_uri)
    preds = model.predict(X_test)
    print(f"\n{model_uri}")
    print(f"  run_id    = {model.metadata.run_id}")  # model được load từ run nào
    print(f"  rows      = {len(X_test)}   first 10 preds = {list(preds[:10])}")
    print(f"  accuracy  = {accuracy_score(y_test, preds):.4f}")


def main() -> None:
    connect()
    X_train, X_test, y_train, y_test = get_data()

    # Alias được dịch sang version NGAY LÚC GỌI — đổi alias ở bài 18 thì dòng này đổi theo
    mv = MlflowClient().get_model_version_by_alias(MODEL_NAME, ALIAS)
    print(f"@{ALIAS} hiện trỏ tới version {mv.version}")

    load_and_score(f"models:/{MODEL_NAME}@{ALIAS}", X_test, y_test)
    load_and_score(f"models:/{MODEL_NAME}/{VERSION}", X_test, y_test)
    # → cùng run_id, cùng accuracy: hai URI khác nhau nhưng cùng một model

    # Extend dòng 23:  X_test, _, _, _ = get_data()
    # get_data trả X_train ĐẦU TIÊN → biến tên "X_test" thật ra là X_train.
    # Không có lỗi nào — chỉ predict nhầm tập (dữ liệu model đã học).
    x_named_test, _, _, _ = get_data()
    print(f"\nExtend dòng 23 predict {len(x_named_test)} hàng (= X_train {len(X_train)}), "
          f"dòng 32 predict {len(X_test)} hàng (= X_test).")


if __name__ == "__main__":
    main()
