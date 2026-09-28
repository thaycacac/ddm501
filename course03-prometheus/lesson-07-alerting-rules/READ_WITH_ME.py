"""
BÀI 07 — Alerting rules
         (= tutorial06: monitoring/prometheus/alerts/model.yml, rule_files trong
            prometheus.yml; câu 4 của checklist README; ảnh screenshots/02, 04, 05)

1) Alert = một câu PromQL + thời gian chờ

   Prometheus chạy mọi `expr` mỗi evaluation_interval. Alert "đúng" khi expr TRẢ VỀ
   ÍT NHẤT MỘT SERIES (so sánh > / == là bộ lọc — bài 05). Mỗi series trả về = một alert.

2) Ba trạng thái

   inactive  expr rỗng
   pending   expr có kết quả, đang đếm `for:`
   firing    expr có kết quả liên tục suốt `for:` → mới thật sự báo
   Xem ở trang /alerts, hoặc query metric tự sinh: ALERTS{alertstate="firing"}.

3) `for:` — phần người mới hay bỏ rồi hối hận

   Không có `for:`: một lần scrape vượt ngưỡng (một cú giật) là báo → báo động giả →
   người trực quen bỏ qua → sự cố thật cũng bị bỏ qua. `for:` đòi điều kiện đúng LIÊN TỤC.
   Đánh đổi: `for:` dài → ít báo giả, nhưng báo trễ. Sự cố nặng (ApiDown) → `for:` ngắn;
   xu hướng chậm (drift) → `for:` dài.

4) Viết alert từ CÂU HỎI đáng đánh thức ai đó dậy — không phải từ metric có sẵn

   ApiDown             up == 0                       không scrape được
   ModelNotLoaded      wdbc_model_loaded == 0        sống mà vô dụng
   HighErrorRate       tỉ lệ lỗi > 5%                tỉ lệ, không phải số đếm
   SlowPredictions     p95 > 50 ms                   cái đuôi, không phải trung bình
   MalignantShareShift |share − 0.37| > 0.15         câu trả lời đổi — chỉ ML mới có

5) labels và annotations

   labels       gắn vào alert, dùng để ĐỊNH TUYẾN (severity: critical → gọi điện).
   annotations  chữ cho người đọc, có template:
                {{ $labels.instance }}  giá trị label của series gây alert
                {{ $value }}            giá trị series expr trả về — với "A > 0.05" là giá trị
                                        của A (vd 0.2), không phải true/false
                | humanizePercentage    0.2 → 20%     | humanizeDuration  0.21 → 210ms

6) Prometheus chỉ ĐÁNH GIÁ; gửi thông báo là việc của Alertmanager

   Tutorial06 không có Alertmanager — alert chỉ hiện ở trang /alerts. Gửi Slack/email/
   gom nhóm/tắt tiếng là phần Bonus.

7) Kiểm tra cú pháp trước khi nạp

   docker compose exec prometheus promtool check rules /etc/prometheus/alerts/model.yml

File:
  docker-compose.yml          như bài 04 + mount thư mục alerts
  prometheus/prometheus.yml   thêm rule_files
  prometheus/alerts/model.yml 5 alert (for/cửa sổ rút ngắn, giá trị gốc ghi ở comment "t06:")

TỔNG KẾT
  - Alert = expr PromQL có phép so sánh; "đúng" khi trả về series. Mỗi series = một alert.
  - inactive → pending (đếm for:) → firing. Expr rỗng lại → inactive, bộ đếm reset.
  - `for:` chống báo động giả; thiếu for: gần như luôn là nguyên nhân báo giả. Đánh đổi độ trễ.
  - Viết alert từ câu hỏi đáng báo động; dùng tỉ lệ và percentile, không dùng số đếm/trung bình.
  - labels (severity) để định tuyến; annotations để người đọc, có template $labels/$value.
  - Nạp bằng rule_files; kiểm tra bằng promtool check rules; sửa xong POST /-/reload.
  - Prometheus chỉ đánh giá alert; gửi thông báo là Alertmanager (tutorial06 không có).
  - MalignantShareShift: mọi tín hiệu kỹ thuật đều khỏe mà vẫn firing — chỉ ML mới có.
"""
print(__doc__)
