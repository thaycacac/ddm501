"""
BÀI 04 — Idempotency: chạy lại bao nhiêu lần cũng ra cùng kết quả
         (= tutorial04: run_dir, ingest, split, report + backfill)

Idempotent = chạy lại một ngày N lần → kết quả giống hệt chạy 1 lần.
Airflow SẼ chạy lại: retry khi lỗi, bạn bấm Clear, backfill chạy bù...
→ pipeline phải an toàn khi chạy lại, nếu không mỗi lần chạy lại là một lần hỏng dữ liệu.

4 kỹ thuật trong tutorial04 (bài này tự viết lại cả 4):

1) Mỗi ngày một thư mục:  data/staging/<ds>/
     run_dir(ds) → chạy lại ngày 25 chỉ GHI ĐÈ thư mục 2026-09-25, không đụng ngày khác.
     (Bài 02: dùng ds, không dùng datetime.now().)

2) Snapshot nguồn một lần (task ingest)
     Đọc data/raw/*.csv MỘT lần, lưu thành raw.parquet trong thư mục của ngày.
     Task sau đọc raw.parquet, không đọc lại CSV → nếu nguồn đổi giữa chừng,
     mọi task trong run vẫn thấy CÙNG một dữ liệu.

3) Chia train/test bằng HASH của id, không dùng random seed
     hash(id) % 100 < 20  → test
     - Cùng id → luôn cùng phía, trên mọi máy, mọi lần chạy.
     - Seeded shuffle chỉ ra cùng kết quả nếu các dòng đến ĐÚNG THỨ TỰ cũ và
       KHÔNG thêm dòng mới. Nguồn thay đổi một chút là cả tập test đổi.

4) Log chung không bị nhân đôi (history.jsonl)
     Đọc file → BỎ dòng có cùng ds → thêm dòng mới → ghi lại cả file.
     So sánh: append thẳng (history_naive.jsonl) → chạy lại 2 lần = 2 dòng trùng.

Backfill = chạy bù một khoảng ngày bằng CLI (catchup=False vẫn backfill được):
     airflow dags backfill <dag_id> -s 2026-09-22 -e 2026-09-24
     → 3 run, run_id "backfill__...", 3 thư mục ngày.

File trong bài:
  docker-compose.yml            như bài 03 (mount ./scripts)
  data/raw/orders.csv           nguồn: 20 đơn hàng (order_id, amount)
  dags/idempotent_pipeline.py   ingest → split → report (+ report_naive để so sánh)
  scripts/compare_splits.py     hash split vs seeded shuffle khi nguồn thay đổi
"""
print(__doc__)
