"""
BÀI 02 — Histogram và Gauge
         (= tutorial06: LATENCY, MODEL_LOADED, MODEL_INFO, MALIGNANT_SHARE trong
            app/metrics.py dòng 32–67; LATENCY.observe trong app/main.py dòng 77–80;
            câu 2 và 3 của checklist README)

1) Vì sao trung bình nói dối

   Hai hệ thống, cùng latency TRUNG BÌNH ≈ 40 ms:
     steady : mọi request đều ~40 ms                         → không ai khổ
     spiky  : 90% request 10 ms, 10% request 310 ms          → 1/10 người dùng chờ 0,3 giây
   Trung bình = (tổng thời gian) / (số request) → ra cùng một con số, che mất cái ĐUÔI.
   Thứ phân biệt được hai hệ thống: PERCENTILE. p95 = "95% request nhanh hơn mức này".
     steady: p95 ≈ 45 ms       spiky: p95 ≈ 300+ ms

2) Histogram — đếm theo "xô" (bucket)

   Histogram("demo_latency_seconds", ..., buckets=(0.005, 0.01, 0.025, 0.05, 0.1, ...))
   Mỗi lần .observe(0.012) → cộng 1 vào MỌI bucket có giới hạn trên (le) >= 0.012.

   Trên /metrics một histogram sinh ra NHIỀU series:
     demo_latency_seconds_bucket{le="0.01"}   900     ← số request <= 10 ms
     demo_latency_seconds_bucket{le="0.025"}  900     ← số request <= 25 ms (CỘNG DỒN)
     ...
     demo_latency_seconds_bucket{le="+Inf"}  1000     ← mọi request = _count
     demo_latency_seconds_sum                40.0     ← tổng số giây
     demo_latency_seconds_count              1000     ← tổng số lần observe

   - le = "less than or equal". Bucket CỘNG DỒN: le càng lớn, số càng lớn (hoặc bằng).
   - Trung bình = _sum / _count (vẫn tính được, nhưng biết là nó nói dối).
   - Percentile ƯỚC LƯỢNG từ bucket: p95 nằm ở bucket đầu tiên chứa >= 95% request,
     rồi NỘI SUY tuyến tính trong bucket đó. Đây là việc histogram_quantile() làm (bài 06).
     scripts/read_histogram.py tự cài lại thuật toán này để bạn nhìn thấy.

3) Chọn bucket là một QUYẾT ĐỊNH, không phải chi tiết

   Độ chính xác của percentile phụ thuộc bucket có "bao quanh" các giá trị bạn quan tâm không.
   - Mặc định của thư viện: 5 ms → 10 s. Model sklearn trả lời trong 2–3 ms → gần như
     mọi request rơi vào bucket đầu → p95 vô nghĩa. Vì vậy tutorial06 tự đặt 1 ms → 1 s.
   - Giá trị vượt bucket lớn nhất chỉ rơi vào +Inf → percentile bị "kẹt" ở mép trên
     (tutorial06: "p95 trên 1 s sẽ đọc thành đúng 1 s").
   - Mỗi bucket = 1 series nữa → đừng đặt 100 bucket.

4) Gauge — con số lên xuống được

   .set(x) / .inc() / .dec(). Dùng cho MỨC hiện tại: độ sâu hàng đợi, RAM, nhiệt độ,
   cờ có/không (1/0). Đọc TRỰC TIẾP giá trị gauge là có nghĩa (khác Counter).
   Tutorial06:
     wdbc_model_loaded     1/0 — "có model để phục vụ không"
     wdbc_malignant_share  tỉ lệ ác tính trong 200 dự đoán gần nhất (bài 09)

5) Info pattern — gauge luôn bằng 1, thông tin nằm ở LABEL

   demo_model_info{version="1.0.0", sklearn_version="1.6.0"} 1
   Giá trị không quan trọng. Label mới là dữ liệu: "lúc 14:20 version nào đang chạy?"
   → trả lời bằng một đường trên biểu đồ thay vì đoán. (checklist câu 3)

6) (Biết để tránh) Summary
   Summary tính percentile NGAY TRONG process. Nghe tiện, nhưng không cộng gộp được
   giữa nhiều instance (p95 của 3 server ≠ trung bình 3 p95). Histogram gộp được
   (cộng bucket lại rồi mới tính) → gần như luôn chọn Histogram.

File:
  latency_demo.py            2 hệ thống steady/spiky + các gauge, mở /metrics ở port 28001
  scripts/read_histogram.py  đọc bucket, tính trung bình và tự ước lượng p50/p95/p99

TỔNG KẾT
  - Trung bình che cái đuôi: 40 ms trung bình có thể là "ai cũng 40 ms" hoặc
    "90% 10 ms, 10% 310 ms". Percentile (p50/p95/p99) mới phân biệt được — xem NHIỀU
    percentile, vì một percentile nằm đúng ranh giới có thể bỏ sót đuôi.
  - Histogram = đếm theo bucket CỘNG DỒN: _bucket{le=...}, le="+Inf" = _count, thêm _sum.
    Trung bình = _sum / _count.
  - Percentile là ƯỚC LƯỢNG: tìm bucket chứa rank, nội suy tuyến tính (giả định phân bố
    đều trong bucket). Bucket rộng → sai số lớn.
  - Chọn bucket là quyết định thiết kế:
      * dày quanh vùng quan tâm (quanh ngưỡng alert);
      * phải BAO được giá trị lớn — vượt bucket cuối thì percentile kẹt ở mép trên
        → alert "p95 > X" với X lớn hơn bucket cuối sẽ không bao giờ kêu;
      * mỗi bucket = thêm 1 series → đừng đặt quá nhiều.
  - Gauge = mức hiện tại, lên xuống được, đọc thẳng là có nghĩa (hàng đợi, cờ 1/0).
  - Info pattern: gauge luôn = 1, thông tin chuỗi nằm ở label (giá trị metric chỉ là số).
  - Chọn Histogram thay Summary: histogram cộng gộp được giữa nhiều instance.
  - Tutorial06: LATENCY (histogram, bucket 1 ms → 1 s), MODEL_LOADED (cờ), MODEL_INFO (info).
"""
print(__doc__)
