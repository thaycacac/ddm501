"""
BÀI 17 — Train + log + register có signature  (= tutorial02-extend/01_training.py)

Hạ tầng xong ở bài 16. Từ bài này chỉ còn code Python, chạy trên stack bài 16.

01_training.py làm 2 run, mỗi run ra 1 version trong registry:

  run "…_v1"  RandomForest     log_model(..., registered_model_name=NAME)
              → version 1, KHÔNG có signature
  run "…_v2"  RandomForest     log_model(..., signature=..., input_example=...,
              (nhiều cây hơn)              registered_model_name=NAME)
              → version 2, CÓ signature

Đã biết (bài 05, 08, 09):  tags / params / metrics, log_model, register_model
Mới ở bài này:
  1. registered_model_name=  → log + register trong MỘT lệnh
                               (bài 09 bạn gọi mlflow.register_model riêng)
  2. signature               → "hợp đồng" input/output lưu trong file MLmodel
  3. input_example           → vài hàng mẫu lưu cạnh model (input_example.json)
  4. Mọi thứ trên giờ nằm ở Postgres (metadata) + MinIO (file) — bài 13–16

Một model sau khi register nằm ở 3 tầng:
  Registered model  course-17-classifier
    └── Version 2   (trỏ về runs:/<run_id>/model)
          └── Run   params / metrics / tags lúc train
                └── Artifacts trong MinIO: MLmodel, model.pkl, input_example.json...

File trong bài:
  connect.py                  đọc .env của stack bài 16
  data.py                     = tutorial02-extend/utils/data.py (numpy, stratify)
  step1_train_and_register.py = 01_training.py, viết lại có comment
  step2_inspect_versions.py   đi từ version → run → file trong MinIO

Thứ tự học: làm theo hướng dẫn trong chat, từng bước một.
"""
print(__doc__)
