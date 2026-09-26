"""
BÀI 04 bước 4 — CỐ Ý không gọi set_tracking_uri.

MLflow mặc định ghi vào thư mục local ./mlruns (file store).
Server UI ở http://127.0.0.1:5001 ĐỌC DB/artifacts KHÁC → bạn sẽ không thấy run này trên UI.

Sau demo: ls ./mlruns  và so với UI. Rồi chạy lại log_one_run.py (có connect()).
"""
from __future__ import annotations

import mlflow

# CỐ Ý không set_tracking_uri.
mlflow.set_experiment("ghost-not-on-server-ui")

with mlflow.start_run(run_name="lost-from-ui") as run:
    mlflow.log_metric("x", 1.0)
    print(f"run_id         = {run.info.run_id}")
    print(f"tracking_uri   = {mlflow.get_tracking_uri()}")
    print("→ URI kiểu file:./mlruns = KHÔNG phải server :5001")
    print("→ Mở UI :5001 sẽ KHÔNG thấy run này (đúng như thiết kế demo).")
