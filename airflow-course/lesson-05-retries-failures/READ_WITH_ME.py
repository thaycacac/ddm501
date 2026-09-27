"""
BÀI 05 — Lỗi và retry
         (= tutorial04: default_args dòng 45–49, task validate dòng 71–105,
            scripts/corrupt_extract.py, bài tập 2 và 4 của README)

1) Hai loại lỗi, hai cách xử lý

   Lỗi TẠM THỜI (mạng chập chờn, DB bận, API timeout)
     → thử lại có thể thành công → dùng RETRY.
   Lỗi VĨNH VIỄN (file hỏng, schema sai, dữ liệu bẩn quá nhiều)
     → thử lại 100 lần vẫn hỏng → FAIL NGAY, đừng phí thời gian retry.

2) Retry trong default_args (áp dụng cho MỌI task của DAG)

   default_args={
       "retries": 3,                        # tối đa 3 lần thử lại (tổng 4 lần chạy)
       "retry_delay": timedelta(seconds=10),# chờ trước lần thử lại
       "retry_exponential_backoff": True,   # mỗi lần chờ lâu hơn: ~10s, ~20s, ~40s...
   }
   Trạng thái trên Grid: running → up_for_retry (vàng) → running → ... → success / failed
   Mỗi lần thử có log riêng: attempt=1.log, attempt=2.log, ...

3) AirflowFailException = "đừng retry"
   raise AirflowFailException("...") → task FAILED ngay, bỏ qua mọi retry còn lại.
   Log ghi: "Immediate failure requested".
   Mọi exception khác (ValueError, ConnectionError...) → được retry theo default_args.

4) Quarantine + ngưỡng (task validate của tutorial04)
   - Không fail vì MỘT dòng xấu: tách dòng xấu ra rejected.parquet (cách ly),
     giữ dòng sạch ở clean.parquet, ghi validation_report.json (lỗi gì, bao nhiêu).
   - Chỉ fail cả run khi tỉ lệ dòng xấu > ngưỡng (5%): nguồn hỏng nặng, dùng tiếp là sai.
   - Task sau (report) bị upstream_failed → không có output sai nào được tạo ra.

DAG trong bài:
  lesson05_retry_demo    1 task giả lập mạng chập chờn: lỗi lần 1, 2 — thành công lần 3
  lesson05_quarantine    ingest → validate → report (giống tutorial04, rút gọn)

File:
  data/raw/readings.csv        40 dòng độ ẩm (reading_id, humidity, status); có sẵn 1 dòng xấu
  dags/retry_demo.py
  dags/quarantine_pipeline.py
  scripts/corrupt_source.py    làm hỏng 15% dòng (--repair để khôi phục) = corrupt_extract.py
  scripts/show_rejected.py     in các dòng bị cách ly của một ngày
"""
print(__doc__)
