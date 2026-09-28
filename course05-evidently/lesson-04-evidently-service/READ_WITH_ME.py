"""
BÀI 04 — Đưa Evidently thành service FastAPI + metric Prometheus
         (= tutorial07: toàn bộ evidently/main.py, evidently/Dockerfile, service `evidently`
            trong docker-compose.yml dòng 242–265)

1) Vì sao phải thành service

   Bài 01–03 là script chạy tay. Ở production cần một tiến trình sống lâu:
     - GOM dữ liệu: API dự đoán (hoặc simulations) gửi từng mẫu vào /capture
     - GIỮ reference: POST /reference một lần, lưu đĩa
     - PHÂN TÍCH theo lịch: Airflow gọi POST /analyze (DAG drift_monitoring)
     - XUẤT KẾT QUẢ thành số: gauge trên /metrics → Prometheus scrape → alert/Grafana (bài 05)

       simulations ──/capture──► [buffer RAM] ──┐
       admin ──────/reference──► [đĩa]  ────────┼─► /analyze ─► Report ─► gauge ─► /metrics ◄─ Prometheus
       Airflow ────/analyze────────────────────┘                  └─► HTML /reports

2) Endpoint (giữ nguyên hợp đồng của tutorial07)

   POST /capture         {features:{...}, prediction, timestamp, model_version}
   POST /capture/batch   {data:[{...}, ...]}
   GET|POST /reference   xem / thay reference (lưu reference_data.csv + metadata.json)
   POST /analyze         {window_size, threshold, stattest_threshold} → kết quả + report_url
   GET /reports, /reports/{name}   HTML của Evidently
   DELETE /production-data         xóa buffer
   GET /health, /metrics

3) Những gì service của khóa sửa so với tutorial07

   | tutorial07                                         | service bài 04                                  |
   |----------------------------------------------------|-------------------------------------------------|
   | đọc drift_by_columns từ DatasetDriftMetric → rỗng  | đọc từ DataDriftTable                           |
   | evidently_feature_drift không bao giờ có series    | có, + evidently_feature_drift_score{stattest}   |
   | threshold nhận vào rồi bỏ qua                      | threshold = drift_share của DataDriftPreset     |
   | drift_score = share nếu drift, ngược lại 0         | drift_score = share thật (0.27 vẫn là 0.27)     |
   | evidently_missing_values_ratio khai báo, không set | set từ tỷ lệ NaN của current                    |
   | EVIDENTLY_MIN_SAMPLES... khai báo trong compose,   | đọc thật; < MIN_SAMPLES → 400 (DAG coi là skip) |
   |   main.py không đọc                                |                                                 |
   | không biết lần phân tích cuối lúc nào              | evidently_last_analysis_timestamp_seconds       |
   | async def analyze → Evidently chặn event loop      | def analyze → chạy trong threadpool             |
   | HTML tích mãi không xóa                            | giữ EVIDENTLY_KEEP_REPORTS file mới nhất        |

   Hệ quả với alert của tutorial07 (bài 05 xử lý): MultipleDriftedFeatures, missing-value
   alerts, ModerateDriftScore (0.2 < score <= 0.5 — không thể xảy ra khi score chỉ khác 0
   lúc share >= 0.5) đều KHÔNG BAO GIỜ bắn được với code gốc.

4) Hai điều về gauge cần nhớ

   - Gauge giữ giá trị của LẦN PHÂN TÍCH CUỐI tới khi có lần mới. Không phân tích nữa thì số
     vẫn nằm đó, trông như "vẫn ổn" → cần gauge timestamp để phát hiện "lâu không chạy".
   - Restart container: gauge về 0, counter về 0, buffer RAM mất; reference và HTML còn (volume).

5) Không phải lỗi nhưng nên biết

   - Buffer production chỉ ở RAM (tối đa 10000 mẫu). Production thật: ghi DB/object storage.
   - window_size=100 và reference vài trăm dòng → KS → drift_score từng cột là p-value.

File:
  app/main.py            service (comment giải thích từng quyết định, đánh số chỗ sửa lỗi)
  app/Dockerfile         python:3.10-slim, healthcheck bằng Python
  app/requirements.txt   cùng phiên bản với tutorial07
  docker-compose.yml     port 28101, volume reference + reports, env đọc thật
  scripts/client.py      health / reference / capture / analyze / metrics / reset

TỔNG KẾT
  - Service drift = gom mẫu (/capture) + giữ reference + phân tích theo lịch (/analyze) +
    xuất gauge (/metrics) + lưu HTML.
  - Kết quả Evidently → gauge: dataset (drift_detected, drift_score=share, drifted_count) và
    từng feature (feature_drift, feature_drift_score có label stattest, missing_ratio).
  - Code tính nặng trong FastAPI dùng `def`, không `async def`.
  - Gauge chỉ là ảnh chụp lần phân tích cuối → luôn kèm timestamp; restart làm mất RAM và metric.
  - tutorial07 sai ở chỗ đọc as_dict, bỏ qua threshold, ép drift_score về 0, bỏ trống
    missing_ratio → nhiều alert drift không thể bắn.
"""
print(__doc__)
