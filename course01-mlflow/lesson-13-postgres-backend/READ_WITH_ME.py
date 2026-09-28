"""
BÀI 13 — Postgres làm "backend store" cho MLflow (thay cho SQLite)

Bạn đã biết (Tutorial 02, bài 06, bài 12):
  mlflow server --backend-store-uri sqlite:///mlflow.db
  → metadata (experiment, run, param, metric, tag, registry) nằm trong 1 FILE .db

Bài này đổi ĐÚNG MỘT thứ:
  mlflow server --backend-store-uri postgresql://mlflow:mlflow@127.0.0.1:25432/mlflow
  → metadata nằm trong một DATABASE SERVER (Postgres) chạy trong Docker

Artifact (file) VẪN nằm trên đĩa máy bạn (./mlartifacts) — bài 14–15 mới chuyển
sang MinIO. Đổi từng mảnh một để thấy rõ mảnh đó làm gì.

Vì sao tutorial02-extend bỏ SQLite?
  - SQLite = 1 file, khóa cả file khi ghi. Nhiều process ghi cùng lúc dễ lỗi
    "database is locked". tutorial02-extend chạy mlflow với --workers 4 (4 process).
  - Postgres = server riêng, nhiều kết nối đồng thời, nhiều máy dùng chung được.
  - Tách hẳn khỏi container MLflow: MLflow chết/ build lại, dữ liệu vẫn ở Postgres.

Cấu trúc URI (giống hệt dòng 61 trong tutorial02-extend/docker-compose.yml):

    postgresql://mlflow:mlflow@127.0.0.1:25432/mlflow
    └ driver ┘   └user┘ └pass┘ └─ host ─┘ └port┘ └db┘

  Khác nhau duy nhất: trong compose của extend, MLflow chạy TRONG Docker nên
  host là "postgres" (tên service) và port là 5432 (port bên trong container).
  Ở bài này MLflow chạy NGOÀI Docker (trên máy bạn) → 127.0.0.1:25432.

Tracking URI vẫn là http://127.0.0.1:5001 như bài 04–11: script ML không đổi
một dòng nào, chỉ server phía sau đổi backend.

File trong bài:
  docker-compose.yml       service postgres — tương đương dòng 5–22 của extend
  connect.py               TRACKING_URI / EXPERIMENT (như bài 04–11) + PG để mở nắp DB
  step1_hello_postgres.py  gõ cửa Postgres, liệt kê bảng
  step2_log_run.py         log 1 run → tìm metadata trong Postgres, file trên đĩa

Thứ tự học: làm theo hướng dẫn trong chat, từng bước một.
"""
print(__doc__)
