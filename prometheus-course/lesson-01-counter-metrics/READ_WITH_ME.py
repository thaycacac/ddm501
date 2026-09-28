"""
BÀI 01 — /metrics, pull model và Counter
         (= tutorial06: endpoint /metrics trong app/main.py dòng 97–102,
            Counter PREDICTIONS / ERRORS trong app/metrics.py dòng 14–29,
            bài tập 1 của README)

1) Monitoring khác logging thế nào

   Log   = từng sự kiện riêng lẻ, dạng chữ: "14:20:01 predict sample WDBC-0001 → benign".
           Tốt để điều tra MỘT request. Tệ để trả lời "bao nhiêu / nhanh hay chậm / tăng hay giảm".
   Metric = con số được đo liên tục theo thời gian: "đã phục vụ 3412 dự đoán".
           Rẻ, nhỏ, gộp được, vẽ được biểu đồ, đặt được cảnh báo.
   Tutorial06 mở đầu bằng 5 câu hỏi không trả lời được nếu không có metric:
   bao nhiêu dự đoán? bao nhiêu % lỗi? chậm hơn tuần trước không? version nào? kết quả có lệch không?

2) Pull model — Prometheus ĐI LẤY, service KHÔNG GỬI

   Service chỉ mở một trang text tên /metrics. Nó không biết Prometheus tồn tại.
   Prometheus định kỳ (scrape_interval, vd 5s) gọi GET /metrics và lưu lại các con số.

       [service] --(mở /metrics)-->  <--(GET mỗi 5s)-- [Prometheus]

   Hệ quả quan trọng: nếu service chết, Prometheus lấy không được → chính sự VẮNG MẶT là
   tín hiệu (metric `up` = 0, bài 04). Service không cần "tự báo tin mình chết".
   (Push model ngược lại: service tự gửi số đi, vd StatsD — tutorial07 có dùng.)

3) Exposition format — toàn bộ "hợp đồng" giữa service và Prometheus

   # HELP demo_requests_total Số request đã xử lý, theo kết quả.
   # TYPE demo_requests_total counter
   demo_requests_total{status="ok"} 412.0
   demo_requests_total{status="error"} 47.0

   - # HELP : mô tả cho người đọc.
   - # TYPE : loại metric (counter / gauge / histogram / summary).
   - Mỗi dòng còn lại = <tên>{<label>="<giá trị>",...} <số>

4) Time series = tên metric + MỘT tổ hợp giá trị label

   demo_requests_total{status="ok"} và demo_requests_total{status="error"}
   là HAI time series khác nhau dưới cùng một tên. Prometheus lưu, đánh index và
   giữ trong RAM theo từng series → số series là chi phí thật (bài 10: cardinality).

5) Counter — chỉ tăng (hoặc về 0 khi process restart)

   - .inc() / .inc(n). KHÔNG có .dec(). Muốn lên xuống → Gauge (bài 02).
   - Tên nên có hậu tố _total. prometheus_client tự thêm _total nếu bạn quên.
   - Gần như KHÔNG BAO GIỜ đọc giá trị Counter trực tiếp: "412 request kể từ lúc
     process khởi động" vô nghĩa nếu không biết process khởi động khi nào.
     Thứ cần đọc là TỐC ĐỘ TĂNG: (giá trị sau − giá trị trước) / số giây
     → "bao nhiêu request/giây ngay lúc này". Đó là rate() của PromQL (bài 05).
     Bài này bạn tự tính bằng tay bằng scripts/manual_rate.py.
   - Restart process → counter về 0. rate() của Prometheus nhận ra "số giảm = reset"
     và xử lý đúng. Bạn sẽ tự thấy hiện tượng reset ở bước cuối.
   - Mỗi series counter đi kèm một series <tên>_created (TYPE gauge) = thời điểm
     (Unix timestamp) series đó được tạo. prometheus_client tự sinh; bạn không cần dùng.

File:
  counter_demo.py         service giả lập: mở /metrics ở port 28001, tăng counter theo status
  scripts/manual_rate.py  lấy /metrics 2 lần, tự tính request/giây = việc rate() làm

TỔNG KẾT
  - Metric = con số đo theo thời gian; log = sự kiện riêng lẻ. Hỏi "bao nhiêu / nhanh
    hay chậm / tăng hay giảm" → metric.
  - Pull model: service chỉ mở /metrics, Prometheus tự đến lấy. Service chết → lấy
    không được → up = 0. Không ai phải tự báo mình chết.
  - /metrics là text: # HELP (mô tả), # TYPE (loại), rồi <tên>{label="..."} <số>.
  - Time series = tên + MỘT tổ hợp giá trị label. Label 2 giá trị → 2 series.
    Series chỉ xuất hiện sau lần .labels(...) đầu tiên.
  - Counter chỉ tăng, về 0 khi restart. Không đọc giá trị tuyệt đối — đọc TỐC ĐỘ TĂNG
    (hiệu số / số giây) = rate(). Gặp số giảm → coi là reset, tính từ 0, không ra số âm.
  - Tỉ lệ lỗi phải tính trên một KHOẢNG thời gian, không trên tổng tích lũy — 3 tuần
    ổn định sẽ làm loãng 5 phút lỗi 50%.
  - Mỗi counter kèm series _created (thời điểm tạo) — tự sinh, bỏ qua được.
  - Tutorial06: wdbc_predictions_total{outcome}, wdbc_errors_total{reason} là Counter có label.
"""
print(__doc__)
