"""
BÀI 03 — Gắn metric vào service FastAPI chấm điểm WDBC
         (= tutorial06: toàn bộ app/metrics.py, app/main.py, scripts/traffic.py,
            scripts/train_model.py; bài tập 1 và 3 của README)

Bài 01–02 dùng script giả lập. Bài này là service THẬT: model sklearn chấm điểm
ung thư vú (WDBC), mỗi request /predict được đo. Code gần như y hệt tutorial06 —
học xong bài này là đã đọc được app/ của tutorial06.

1) Năm câu hỏi → năm nhóm metric (mở đầu tutorial06)

   Câu hỏi                                   Metric                              Loại
   Đã phục vụ bao nhiêu dự đoán?             wdbc_predictions_total{outcome}     Counter
   Bao nhiêu % request lỗi?                  wdbc_errors_total{reason}           Counter
   Có chậm hơn tuần trước không?             wdbc_prediction_latency_seconds     Histogram
   Version nào đang chạy?                    wdbc_model_info{version,...}        Gauge (info)
   Kết quả có còn giống lúc deploy không?    wdbc_malignant_share                Gauge
   (+ có model để phục vụ không?)            wdbc_model_loaded                   Gauge 1/0

   Nguyên tắc: thiết kế metric TỪ CÂU HỎI, không phải "thấy gì đo nấy".

2) /metrics trong FastAPI — không cần start_http_server

   @app.get("/metrics")
   def metrics(): return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)

   generate_latest() = đọc TẤT CẢ metric đã khai báo (trong REGISTRY mặc định) và
   in ra đúng định dạng bạn đã thấy ở bài 01. Khác bài 01: metric được phục vụ
   CÙNG port với API (28000), không cần port riêng.

3) Đếm lỗi theo LÝ DO, không chỉ đếm "có lỗi"

   wdbc_errors_total{reason="missing_features"}   ← client gửi thiếu field (lỗi của client, 422)
   wdbc_errors_total{reason="model_not_loaded"}   ← service không có model (lỗi của ta, 503)
   Hai loại lỗi cần hai phản ứng khác nhau → tách label. reason là tập giá trị
   do CODE quyết định (không phải do người dùng gửi lên) → label an toàn.

4) Đặt bộ đếm giờ đúng chỗ

   start = time.perf_counter()
   ... tạo DataFrame + predict_proba ...
   LATENCY.observe(time.perf_counter() - start)

   Chỉ bao quanh PHẦN VIỆC mà metric muốn nói (model chấm điểm), không bao cả
   request (parse JSON, validate Pydantic...). Tên metric là
   "prediction_latency", nên nó phải đo đúng thời gian dự đoán.
   perf_counter(), không phải time.time(): đồng hồ đơn điệu, không nhảy khi đồng bộ giờ.

5) Cửa sổ trượt bằng deque — metric đi theo DỮ LIỆU, không theo traffic

   recent = deque(maxlen=200)          # tự bỏ phần tử cũ nhất khi đầy
   recent.append(1 if malignant else 0)
   MALIGNANT_SHARE.set(sum(recent) / len(recent))

   Tỉ lệ ác tính trong 200 dự đoán GẦN NHẤT. Vì sao không dùng Counter rồi chia?
   Được (bài 05 làm vậy bằng PromQL), nhưng gauge này cho con số "ngay bây giờ"
   đọc thẳng được, và là metric duy nhất tồn tại VÌ đây là service ML (bài 09).

6) /health nói thật

   Process còn sống nhưng không có model → trả "degraded", model_loaded=false.
   Một container trả 200 trong khi mọi /predict trả 503 còn tệ hơn container chết hẳn.

File:
  data/raw/wdbc.csv           569 mẫu WDBC (copy từ tutorial06)
  scripts/train_model.py      train LogisticRegression → models/model.joblib + model_card.json
  app/metrics.py              khai báo toàn bộ metric
  app/main.py                 FastAPI: /health, /predict, /metrics
  scripts/traffic.py          bắn request: --rps, --seconds, --broken, --drift

TỔNG KẾT
  - Thiết kế metric từ CÂU HỎI: bao nhiêu (Counter), lỗi bao nhiêu và vì sao (Counter
    theo reason), chậm không (Histogram), version nào (info), có model không (gauge 1/0),
    kết quả có lệch không (gauge theo dữ liệu).
  - Khai báo metric ở module riêng, MỘT lần (khai báo lại → lỗi Duplicated timeseries).
  - Trong FastAPI: route /metrics trả generate_latest() với CONTENT_TYPE_LATEST —
    cùng port với API, không cần start_http_server.
  - Label chỉ nhận giá trị do CODE quyết định (outcome, reason), không lấy từ input người dùng.
  - Đồng hồ perf_counter() chỉ bao phần việc metric muốn nói (predict_proba). Request lỗi
    không observe vào latency — lỗi đã có ERRORS; trộn vào sẽ làm latency trông nhanh hơn.
  - Service sống nhưng không có model: /health = degraded, wdbc_model_loaded = 0,
    wdbc_model_info không xuất hiện, mọi /predict → 503. Kiểm tra "port có mở không"
    KHÔNG bắt được — phải có gauge riêng (alert ModelNotLoaded, bài 07).
  - deque(maxlen=200) → wdbc_malignant_share = tỉ lệ ác tính trong 200 dự đoán gần nhất.
    Bình thường ≈ 0.37 (bằng tỉ lệ lúc train) — đó là BASELINE cho bài 09.
  - Dữ liệu drift: API vẫn 200, latency vẫn bình thường, nhưng phân bố dự đoán đổi —
    chỉ metric theo dữ liệu mới thấy.
  - Tutorial06: app/metrics.py + app/main.py giống bài này. T04_TRAP được thêm ở bài 10,
    SLOW_MS (không có trong tutorial06) ở bài 06.
"""
print(__doc__)
