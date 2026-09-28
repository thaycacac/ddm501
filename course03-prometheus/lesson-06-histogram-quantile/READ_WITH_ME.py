"""
BÀI 06 — PromQL với histogram: histogram_quantile, p50/p95/p99
         (= tutorial06: panel 3 "Latency p50 / p95 / p99" trong wdbc.json;
            alert SlowPredictions trong alerts/model.yml, kèm comment về bucket 1s;
            câu 2 của checklist README)

Bài 02 bạn đã tự cài thuật toán ước lượng percentile bằng Python. Bài này dùng hàm có
sẵn của PromQL — cùng thuật toán, nhưng chạy trên LỊCH SỬ trong Prometheus.

Dùng lại stack bài 04. Service có thêm biến SLOW_MS (không có trong tutorial06):
10% request bị chậm thêm SLOW_MS mili giây — để thấy percentile phản ứng.

1) Histogram trong Prometheus là NHIỀU counter

   wdbc_prediction_latency_seconds_bucket{le="0.001"}    counter
   wdbc_prediction_latency_seconds_bucket{le="0.0025"}   counter
   ...
   wdbc_prediction_latency_seconds_sum / _count          counter
   Mọi thứ đều chỉ tăng → phải rate() trước, như mọi counter (bài 05).
   rate(..._bucket[5m]) = "mỗi giây, bao nhiêu request rơi vào <= le, trong 5 phút qua".

2) Công thức chuẩn — thuộc lòng

   histogram_quantile(0.95, sum by (le) (rate(wdbc_prediction_latency_seconds_bucket[5m])))

   Đọc từ trong ra ngoài:
     rate(...[5m])     bucket nào tăng bao nhiêu mỗi giây trong 5 phút qua
     sum by (le)       gộp mọi instance/label khác, nhưng GIỮ le
     histogram_quantile(0.95, ...)  tìm bucket chứa rank 95%, nội suy tuyến tính (bài 02)

   Vì sao "by (le)": histogram_quantile cần label le để biết mép bucket. sum() không by (le)
   → mất le → kết quả rỗng/NaN. Có nhiều instance mà không sum → ra p95 RIÊNG từng instance.

3) p95 của 5 phút qua, không phải của cả đời process

   Nhờ rate(...[5m]), percentile chỉ tính trên request trong cửa sổ. Service chậm 5 phút
   gần đây → p95 tăng ngay, không bị "loãng" bởi hàng giờ chạy nhanh trước đó.
   (read_histogram.py ở bài 02 tính trên TỔNG tích lũy — đó là điểm khác.)

4) Trung bình vẫn tính được — và vẫn nói dối

   rate(..._sum[5m]) / rate(..._count[5m])
   Với SLOW_MS=200: trung bình tăng ~20 ms, p99 tăng ~200 ms. Nhìn trung bình sẽ đánh giá thấp sự cố.

5) Tỉ lệ request đủ nhanh — kiểu SLO

   sum(rate(..._bucket{le="0.005"}[5m])) / sum(rate(..._count[5m]))
   = "bao nhiêu % request xong trong 5 ms". Chính xác tuyệt đối (không nội suy) vì 0.005
   là một mép bucket. Muốn đo SLO ở ngưỡng X → đặt một bucket đúng tại X.

6) Giới hạn: bucket cuối

   Bucket cuối là 1.0 s. Request 2 s rơi vào +Inf → histogram_quantile trả về 1.0 (mép hữu
   hạn cao nhất). Alert "p95 > 1.5s" sẽ không bao giờ kêu. (Comment của SlowPredictions
   trong tutorial06 nói đúng điều này.)

File:
  queries.promql   các câu truy vấn theo thứ tự học
  (dùng lại ../lesson-05-promql-basics/scripts/promql.py để chạy từ terminal)

TỔNG KẾT
  - Histogram = một nhóm counter (_bucket theo le, _sum, _count) → luôn rate() trước.
  - Công thức: histogram_quantile(q, sum by (le) (rate(x_bucket[5m]))). Phải giữ le.
  - Percentile tính trên CỬA SỔ rate → phản ánh 5 phút gần nhất, không bị loãng.
  - Trung bình = rate(_sum)/rate(_count): vẫn tính được, vẫn che cái đuôi.
  - % request dưới ngưỡng = rate(bucket{le="ngưỡng"}) / rate(_count): chính xác nếu ngưỡng
    là mép bucket → đặt bucket tại ngưỡng SLO.
  - Giá trị vượt bucket cuối → quantile kẹt ở mép hữu hạn cao nhất → bucket phải bao
    được ngưỡng alert.
  - Tutorial06: panel 3 = p50/p95/p99 với [1m]; SlowPredictions = p95 [5m] > 0.05 trong 10m.
"""
print(__doc__)
