"""
BÀI 04 — một run tối thiểu để thấy client → server.

Chạy SAU KHI:
  1) mlflow server đã lắng nghe (agent sẽ hướng dẫn)
  2) đã export MLFLOW_TRACKING_URI nếu cần

Khái niệm:
  Experiment = ngăn kéo chứa nhiều run (vd: một bài toán / một dự án)
  Run        = một lần thử (params + metrics + tags + artifacts...)

Block:
  with mlflow.start_run(...):
      ... mọi log trong block thuộc run đó
"""
from __future__ import annotations

import mlflow

from connect import connect


def main() -> None:
    connect()

    with mlflow.start_run(run_name="hello-mental-model") as run:
        # PARAMETER = input (string/number ghi một lần) — "đã thử cấu hình gì"
        mlflow.log_param("lesson", 4)
        mlflow.log_param("note", "client-sends-to-server")

        # METRIC = output số — "kết quả đo được"
        mlflow.log_metric("demo_score", 0.99)

        # TAG = nhãn tìm kiếm / lọc trên UI
        mlflow.set_tag("phase", "mental-model")

        print(f"run_id = {run.info.run_id}")
        print("Mở UI → experiment 'mlflow-course-04' → thấy run hello-mental-model")


if __name__ == "__main__":
    main()
