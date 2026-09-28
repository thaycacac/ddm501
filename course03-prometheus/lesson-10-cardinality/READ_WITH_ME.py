"""
BÀI 10 — Label cardinality: lỗi đắt nhất khi dùng Prometheus
         (= tutorial06: T04_TRAP trong app/metrics.py dòng 9–23 và app/main.py dòng 84–87,
            scripts/count_series.py, bài tập 2 và 5, câu 5 của checklist, mục 6 của PDF)

Dùng lại stack bài 08. Service bài 03 đã có biến T04_TRAP (mặc định 0).

1) Cardinality = số time series

   Mỗi tổ hợp (tên metric + giá trị các label) = MỘT series (bài 01). Prometheus lưu,
   đánh index và giữ trong RAM theo TỪNG series. Số series là chi phí thật: RAM, đĩa,
   thời gian scrape, thời gian query.

   Số series của một metric = tích số giá trị của từng label:
     wdbc_predictions_total{outcome}              2
     + label status_code (5 giá trị)              2 × 5 = 10
     + label sample_id (mỗi bệnh nhân một giá trị) 2 × ∞

2) Bẫy của tutorial06

   T04_TRAP=1 → PREDICTIONS có thêm label sample_id = mã bệnh nhân (do người dùng gửi lên).
   Cùng một lượng traffic:
     sensible labels   ~20 series   ~4 KB /metrics     KHÔNG đổi dù 100 hay 1 triệu request
     với sample_id     hàng trăm+   ~50 KB /metrics     +1 series cho MỖI bệnh nhân mới, mãi mãi
   Vấn đề không phải "lớn", mà là KHÔNG CÓ GIỚI HẠN: bộ WDBC chỉ có 569 mã nên dừng ở đó,
   ngoài đời bệnh nhân mới đến mỗi ngày → series tăng mãi → Prometheus hết RAM và sập,
   kéo theo mọi dashboard và alert của MỌI service khác dùng chung nó.

3) Quy tắc

   Label chỉ được nhận giá trị từ một tập NHỎ, CÓ GIỚI HẠN, BIẾT TRƯỚC:
     được  outcome, reason, status code, method, model version, region, env
     KHÔNG id người dùng/bệnh nhân/đơn hàng, email, URL có tham số, timestamp,
           message lỗi nguyên văn, bất cứ thứ gì người dùng tự gõ vào
   Phép thử: bạn có viết ra được MỌI giá trị label này sẽ nhận không?
   (reason do CODE quyết định → viết ra được; sample_id do người dùng gửi → không.)

4) Vậy thông tin theo từng request để đâu?

   LOG (kèm sample_id, dùng để điều tra một ca cụ thể) hoặc tracing.
   Metric trả lời "bao nhiêu / nhanh hay chậm"; log trả lời "chuyện gì đã xảy ra với ca X".

5) Tắt bẫy không xóa ngay series cũ

   Series biến mất khỏi /metrics → Prometheus ghi "stale marker", query tức thời không còn
   thấy nó, nhưng dữ liệu cũ vẫn nằm trên đĩa đến hết retention (biểu đồ quá khứ vẫn vẽ).
   Bẫy chạy một ngày = rác một ngày.

File:
  scripts/count_series.py   đếm series theo tên metric + kích thước /metrics
  queries.promql            đo cardinality bằng PromQL: count, count by (__name__), tsdb head

TỔNG KẾT
  - Cardinality = số time series = tích số giá trị các label. Mỗi series tốn RAM/đĩa/CPU.
  - Label có giá trị không giới hạn (id, email, URL, timestamp, input người dùng) làm số
    series tăng mãi → Prometheus sập, kéo theo giám sát của mọi service khác.
  - Quy tắc: label chỉ lấy từ tập nhỏ, biết trước. Phép thử: liệt kê được mọi giá trị không?
  - Chi tiết từng request → log/tracing, không phải label.
  - Phát hiện: count_series.py, count by (__name__) ({...}), trang Status → TSDB Status.
  - Tắt label xấu không xóa dữ liệu cũ ngay — rác nằm đến hết retention.
"""
print(__doc__)
