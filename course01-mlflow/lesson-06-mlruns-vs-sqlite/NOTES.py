"""
BÀI 06 — Tracking store: file ./mlruns  vs  server + SQLite

Hai chế độ bạn gặp:

1) KHÔNG bật server, không set_tracking_uri
   → MLflow ghi vào ./mlruns (FileStore)
   → Track run được, UI "mlflow ui" đọc được folder đó
   → Model Registry thường KHÔNG dùng được ổn định (cần database backend)

2) mlflow server --backend-store-uri sqlite:///...
   → Metadata trong SQLite; artifacts trong thư mục riêng
   → UI đi kèm server; Registry hoạt động (Tutorial 02 bắt buộc SQLite/Postgres)

Tutorial 02: "The SQLite backend is not optional" — vì có bước register model.

Bài này bạn sẽ:
  - Thấy register trên file store thất bại / không dùng được như kỳ vọng
  - Register trên server SQLite thành công (bước sau trên chat)
"""
from __future__ import annotations

# Chỉ là module tài liệu. Lệnh thực hành nằm trên chat + các script sibling.
print(__doc__)
