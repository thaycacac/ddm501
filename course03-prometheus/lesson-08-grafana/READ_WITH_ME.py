"""
BÀI 08 — Grafana: provisioning datasource + dashboard JSON
         (= tutorial06: monitoring/grafana/** và service grafana trong docker-compose.yml;
            bảng URL trong README; ảnh screenshots/01, 03)

Prometheus lưu và truy vấn; giao diện /graph của nó để THỬ câu PromQL. Grafana để NHÌN:
nhiều panel trên một màn hình, tự làm mới, đơn vị đẹp, chia sẻ được.

1) Grafana không lưu metric

   Mỗi panel = một (hoặc vài) câu PromQL. Mỗi lần làm mới, Grafana gửi câu đó tới
   Prometheus qua /api/v1/query_range (đúng API bạn đã gọi bằng promql.py ở bài 05)
   rồi vẽ kết quả. Toàn bộ "trí tuệ" nằm trong PromQL bạn học ở bài 05–06.

   [trình duyệt] → [grafana:3000] → (PromQL) → [prometheus:9090] → [api:8000]/metrics

2) Provisioning = cấu hình bằng file, không click

   /etc/grafana/provisioning/datasources/*.yml   tạo datasource lúc khởi động
   /etc/grafana/provisioning/dashboards/*.yml    chỉ chỗ chứa file dashboard JSON
   Lợi ích: `docker compose up` trên máy sạch → dashboard có ngay, giống hệt, nằm trong git.
   Dashboard tạo bằng tay trên UI mất khi xóa volume và không review được.

3) uid nối mọi thứ

   datasource: uid: course-prom
   dashboard JSON: "datasource": {"type": "prometheus", "uid": "course-prom"}
   Lệch uid → panel trống, không báo lỗi rõ ràng. Đây là lỗi provisioning phổ biến nhất.

4) access: proxy và url

   proxy = GRAFANA SERVER gọi Prometheus (không phải trình duyệt) → url dùng tên service
   http://prometheus:9090 trong mạng compose — cùng quy tắc với target ở bài 04.

5) Cấu trúc dashboard JSON (grafana/dashboards/wdbc.json)

   uid, title, refresh ("5s"), time (from now-15m)
   panels[]:
     type          timeseries (biểu đồ đường), stat (một con số / chữ lớn)...
     gridPos       x, y, w, h — lưới 24 cột
     targets[]     câu PromQL: expr, legendFormat ("{{outcome}}" = lấy giá trị label), instant
     fieldConfig   unit: reqps (req/s), percentunit (0.2 → 20%), s (giây → ms tự động)

   Panel 1–4 = dashboard tutorial06. Bài này thêm 2 panel stat:
     5 "Model version serving"  wdbc_model_info, textMode name → info pattern (bài 02) hiện thành chữ
     6 "Alerts firing"          ALERTS{alertstate="firing"} → alert của bài 07 trên cùng màn hình

6) Biến môi trường GF_*

   GF_<SECTION>_<KEY> ghi đè grafana.ini: admin user/pass, tắt đăng ký, bật xem ẩn danh.

File:
  docker-compose.yml                               api + prometheus (cấu hình bài 07) + grafana
  grafana/provisioning/datasources/prometheus.yml  datasource Prometheus, uid course-prom
  grafana/provisioning/dashboards/dashboards.yml   provider: đọc JSON trong /var/lib/grafana/dashboards
  grafana/dashboards/wdbc.json                     6 panel

TỔNG KẾT
  - Grafana không lưu metric: mỗi panel là PromQL gửi tới Prometheus (/api/v1/query_range).
  - Provisioning: datasource + dashboard là FILE trong git → up trên máy sạch là có ngay.
  - uid datasource phải khớp uid trong dashboard JSON; lệch → panel trống không lỗi.
  - access: proxy → Grafana server gọi Prometheus → url = http://<tên service>:9090.
  - Dashboard JSON: panels[] với type, gridPos, targets (expr, legendFormat {{label}}),
    fieldConfig.unit (reqps, percentunit, s).
  - Chọn đơn vị đúng trong Grafana thay vì nhân/chia trong PromQL.
  - updateIntervalSeconds: sửa JSON → Grafana tự nạp lại; sửa trên UI → export đè file để giữ.
  - GF_* cấu hình Grafana bằng biến môi trường.
"""
print(__doc__)
