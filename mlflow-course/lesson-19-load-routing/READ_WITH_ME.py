"""
BÀI 19 — Load model theo alias/version + chia traffic A/B
         (= tutorial02-extend/04_loading_models.py + 05_model_routing.py)

Dùng lại course-17-classifier với alias từ bài 18:  prod → v1,  dev/staging → v2.

1) Hai cách gọi tên một model trong registry  (04_loading_models.py)
     models:/NAME/2       theo SỐ VERSION  → luôn là v2, mãi mãi
     models:/NAME@dev     theo ALIAS       → version mà @dev đang trỏ LÚC LOAD
   Cả hai đều được MLflow dịch ra: version → run → file trong MinIO → tải về → load.

   mlflow.pyfunc.load_model: load dạng "generic" — mọi flavour (sklearn, xgboost,
   pytorch...) đều có chung .predict(). Code phục vụ không cần biết model là gì.

2) Chia traffic  (05_model_routing.py)
     mỗi request: random() < 0.9 → @prod (v1),  ngược lại → @dev (v2)
   ≈ 90% request dùng model ổn định, 10% thử model mới (canary / A/B test).

   Extend gọi load_model trong MỖI request → mỗi lần lại hỏi registry + tải file
   từ MinIO. Chạy demo thì được, phục vụ thật thì chậm. Bước 2 so sánh với cách
   load một lần rồi dùng lại (cache).

File trong bài:
  connect.py         đọc .env bài 16, MODEL_NAME = course-17-classifier
  data.py            = utils/data.py (giống bài 17)
  step1_load.py      = 04_loading_models.py (+ đo accuracy, chỉ ra chỗ lấy nhầm X)
  step2_routing.py   = 05_model_routing.py (+ đếm tỉ lệ, đo thời gian, bản có cache)
"""
print(__doc__)
