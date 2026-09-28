"""
BÀI 04 — Prometheus server trong Docker
         (= tutorial06: monitoring/prometheus/prometheus.yml, docker-compose.yml
            service api + prometheus, Dockerfile, bảng URL trong README)

Bài 01–03 BẠN đóng vai Prometheus (curl, manual_rate.py). Bài này dựng Prometheus thật
để nó tự scrape service bài 03 mỗi 5 giây và LƯU lại lịch sử.

1) Kiến trúc

   [máy bạn] --28000--> [api:8000]  <--GET /metrics mỗi 5s--  [prometheus:9090] <--29090-- [máy bạn]
                         └────────── mạng compose "monitoring" ──────────┘

   - Service api build từ code bài 03 (build context ../lesson-03-instrument-fastapi).
   - Prometheus đọc cấu hình từ prometheus/prometheus.yml (mount :ro).

2) prometheus.yml — ba khái niệm

   global.scrape_interval   bao lâu lấy một lần (5s)
   scrape_configs           danh sách JOB; mỗi job có danh sách TARGET (host:port)
   job / instance           Prometheus tự gắn 2 label này vào mọi series:
                            wdbc_predictions_total{job="wdbc-api", instance="api:8000", outcome="benign", ...}

3) Tên service = tên máy trong mạng compose

   Trong container Prometheus, "localhost" là CHÍNH container Prometheus.
   Muốn gọi container api → dùng tên service "api" và port TRONG container (8000),
   không phải port đã map ra máy (28000). Đây là lý do số 1 khiến target DOWN.

4) Metric `up` — Prometheus tự sinh cho mỗi target

   up{job="wdbc-api"} = 1   scrape thành công
   up{job="wdbc-api"} = 0   scrape thất bại (container chết, sai host, timeout...)
   Service chết thì không tự báo được → Prometheus ghi nhận SỰ VẮNG MẶT. Alert đầu tiên
   ai cũng viết: up == 0 (ApiDown, bài 07).

5) Vận hành

   - Trang Status → Targets: UP/DOWN, lần scrape cuối, lỗi nếu có.
   - Tab Graph: gõ biểu thức (PromQL, bài 05), xem bảng hoặc biểu đồ theo thời gian.
   - retention.time=2d: Prometheus là kho ngắn hạn.
   - --web.enable-lifecycle: sửa prometheus.yml → curl -X POST .../-/reload, không restart.
   - HEALTHCHECK + depends_on: service_healthy: Prometheus chỉ bật khi api đã có model.

File:
  Dockerfile                  image cho code bài 03: train lúc build, user thường, HEALTHCHECK
  docker-compose.yml          api + prometheus, mạng monitoring, volume prometheus_data
  prometheus/prometheus.yml   2 job: wdbc-api (api:8000) và prometheus (tự scrape)
  (traffic: dùng ../lesson-03-instrument-fastapi/scripts/traffic.py, mặc định bắn vào 28000)

TỔNG KẾT
  - Prometheus server = vòng lặp: mỗi scrape_interval, GET /metrics của từng target,
    lưu mỗi số thành một điểm (thời gian, giá trị) của time series tương ứng.
  - Cấu hình tối thiểu: global.scrape_interval + scrape_configs (job_name, targets).
  - Mỗi series được gắn thêm label job và instance → biết số đến từ đâu.
  - Trong compose: target = <tên service>:<port trong container>. "localhost" trong
    container Prometheus là chính Prometheus → DOWN.
  - `up` do Prometheus tự sinh; = 0 khi scrape thất bại → phát hiện service chết mà
    service không cần làm gì.
  - Prometheus lưu LỊCH SỬ (khác curl chỉ thấy hiện tại) → hỏi được "5 phút trước thế nào".
  - Sửa cấu hình: POST /-/reload (cần --web.enable-lifecycle). Dữ liệu ở volume, retention 2d.
  - HEALTHCHECK kiểm tra model_loaded (không chỉ process sống) + depends_on service_healthy.
"""
print(__doc__)
