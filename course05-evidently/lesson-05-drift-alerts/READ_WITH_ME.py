"""
BÀI 05 — Alert drift + Alertmanager + Grafana
         (= tutorial07: config/prometheus/evidently_alerts.yml, job `evidently` trong
            config/prometheus.yml, config/grafana/dashboards/evidently-drift-monitoring.json)

1) Đường đi của một cảnh báo drift

   simulate.py ─/capture/batch─► Evidently ─/analyze─► gauge ◄─scrape 15s─ Prometheus
      ─rule (for: 1m)─► Alertmanager ─route source="course"─► Telegram + webhook-echo
                                    └ không khớp route nào ─► blackhole
   Grafana đọc cùng các gauge đó từ Prometheus.

2) Chạy song song HAI bộ rule để thấy tận mắt cái nào hỏng

   rules/evidently_course.yml             bộ đã sửa, label source=course → gửi Telegram
   tutorial07_evidently_alerts.yml        file gốc mount thẳng → chỉ xem trên /alerts (blackhole)
   Lưu ý: service ở đây là bản ĐÃ SỬA (bài 04), nên vài alert gốc giờ bắn được. Những alert gốc
   vẫn KHÔNG BAO GIỜ bắn dù service đúng — lỗi nằm ngay trong biểu thức:

   | Alert gốc              | Lỗi                                              | Bản sửa                      |
   |------------------------|--------------------------------------------------|------------------------------|
   | NoRecentAnalysis       | time() - (X*0 + time()) = 0 → luôn false          | DriftAnalysisStale dùng gauge |
   |                        |                                                  | last_analysis_timestamp       |
   | CriticalDataCondition  | `A and count(B)` — label hai vế khác nhau → rỗng  | `A and on() count(B)`         |
   | LowAnalysisRate        | rate[15m] với lịch 1h → 0 phần lớn thời gian     | bỏ; Stale đã bao trường hợp   |
   |                        | → báo động giả thường trực                        |                              |
   | DataDriftDetected      | description in $value "consecutive checks" — $value | dùng hàm query lấy share    |
   |                        | luôn là 1                                         |                              |

   Còn với service GỐC của tutorial07 thì thêm: MultipleDriftedFeatures, ModelHealthDegrading
   (count luôn 0), HighMissingValues / CriticalMissingValues / MultipleFeaturesMissingValues
   (gauge không có series), ModerateDriftScore (score chỉ khác 0 khi >= 0.5) — đều câm.

3) Alertmanager cho drift

   - route con `source="course"` → telegram; root receiver = blackhole (receiver rỗng = bỏ).
   - inhibit: EvidentlyServiceDown che mọi alert evidently khác; critical che warning cùng
     [component, type] → HighDriftScore che DataDriftDetected nhưng KHÔNG che HighMissingValues.
   - Dùng lại template telegram.course.message, bot token, chat_id của course04-alertmanager.

4) Grafana

   Hai folder: course (dashboard của khóa) và tutorial07 (dashboard gốc, mount thẳng — datasource
   uid "prometheus-datasource" trùng nên chạy luôn). So sánh: "Feature Drift Matrix" và
   "Missing Values" của bản gốc giờ có số (nhờ service đã sửa); dashboard khóa thêm drift_score
   thô kèm stattest và "lần phân tích cuối cách đây".

5) Bản chất "ảnh chụp" của gauge drift

   - Dừng phân tích: gauge đứng yên ở kết quả cuối → alert drift VẪN firing với số cũ.
     Chỉ DriftAnalysisStale cho biết số đó đã cũ.
   - Restart service: gauge về 0 → alert drift resolved dù không có phân tích nào nói "hết drift".
   - `for:` trên gauge đổi theo lịch phân tích chỉ là độ trễ; chọn for và ngưỡng stale theo chu kỳ DAG.

File:
  docker-compose.yml                 evidently (image bài 04) + prometheus + alertmanager + webhook-echo + grafana
  prometheus/prometheus.yml          scrape evidently, rule_files glob
  prometheus/rules/evidently_course.yml   alert đã sửa, comment đối chiếu từng alert gốc
  alertmanager/alertmanager.yml      route source=course, blackhole, inhibit
  grafana/provisioning/**            datasource uid prometheus-datasource, folder theo thư mục
  grafana/dashboards/evidently-course.json   dashboard của khóa
  scripts/simulate.py                vòng lặp capture + analyze (vai simulations + DAG)

TỔNG KẾT
  - Chuỗi drift → cảnh báo: Evidently gauge → Prometheus rule → Alertmanager route → Telegram.
  - Alert drift chỉ đúng khi metric đúng (bài 04) VÀ biểu thức đúng: cẩn thận `and` giữa hai vế
    khác label (dùng on()), `time() - time()`, rate trên cửa sổ ngắn hơn chu kỳ.
  - Gauge drift là ảnh chụp lần phân tích cuối → luôn có alert "phân tích bị cũ" dựa trên timestamp.
  - Alertmanager: route theo label (source), blackhole cho alert không muốn gửi, inhibit theo
    [component, type] để không che nhầm loại khác.
  - Grafana: provisioning datasource theo uid để dùng lại dashboard; bảng feature phải kèm
    stattest vì drift_score lúc là p-value, lúc là khoảng cách.
"""
print(__doc__)
