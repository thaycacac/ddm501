"""
BÀI 05 — Template tin nhắn
         (= tutorial07: config/alertmanager/templates/telegram.tmpl, alertmanager.yml dòng 10–11
            và 41, external_labels trong config/prometheus.yml dòng 9–12)

1) Template = biến payload (bài 01) thành chữ cho người đọc

   Payload có sẵn mọi thứ: .Status, .CommonLabels, .Alerts (mỗi alert có .Labels, .Annotations,
   .StartsAt, .EndsAt, .GeneratorURL), .ExternalURL. Template chọn cái gì in, in thế nào.
   Không khai báo `message:` → Alertmanager dùng telegram.default.message (bài 04).

   Nối vào config gồm 2 chỗ:
     templates: [/etc/alertmanager/templates/*.tmpl]         nạp file chứa define "..."
     message: '{{ template "telegram.course.message" . }}'   receiver gọi template đó

2) Go template — đủ để đọc telegram.tmpl của tutorial07

   {{ define "x" }} ... {{ end }}      khai báo template con
   {{ if eq .Status "firing" }} ... {{ else }} ... {{ end }}
   {{ range .Alerts }} ... {{ end }}   lặp, bên trong "." = một alert
   {{ with .Annotations.runbook }}{{ . }}{{ end }}   chỉ in khi có
   {{ .Alerts.Firing | len }}  {{ .CommonLabels.severity | toUpper }}   pipe + hàm
   {{- ... -}}                         xóa khoảng trắng/xuống dòng hai bên
   {{/* ... */}}                       comment — KHÔNG lồng nhau được
   .StartsAt.Local.Format "2006-01-02 15:04:05 MST"   định dạng giờ bằng NGÀY MẪU của Go

   .CommonLabels chỉ chứa label mà MỌI alert trong nhóm cùng có → tiêu đề dùng được
   severity/component vì group_by [severity, component] bảo đảm chúng giống nhau.

3) Dữ liệu cho template đến từ đâu

   annotations của rule (Prometheus)   summary, description, runbook, dashboard
   external_labels (Prometheus)        env, cluster — gắn vào MỌI alert gửi đi
   --web.external-url (Prometheus)     generatorURL bấm được (bài 01 thấy hostname container)
   --web.external-url (Alertmanager)   .ExternalURL → link tạo silence

4) Hai cái bẫy khi gửi Telegram với parse_mode HTML

   - Ký tự < > & trong annotation → Telegram trả 400 "can't parse entities", tin KHÔNG đi.
     Lỗi nằm trong log Alertmanager + alertmanager_notifications_failed_total.
   - Giờ: .Local trong container = UTC (tutorial07 in "UTC" dù người đọc ở UTC+7).

5) Xem trước template không cần gửi

   amtool template render --template.glob='/etc/alertmanager/templates/*.tmpl' \
       --template.text='{{ template "telegram.course.message" . }}'
   → render với dữ liệu mẫu của amtool (lỗi cú pháp hiện ngay).

File:
  templates/telegram.tmpl        template riêng, comment giải thích từng dòng
  alertmanager/alertmanager.yml  templates: + message:
  prometheus/prometheus.yml      external_labels
  prometheus/alerts/api.yml      thêm annotation runbook, dashboard
  docker-compose.yml             mount ./templates, --web.external-url cho cả hai

TỔNG KẾT
  - Template chọn trường nào của payload in ra: .Status, .CommonLabels, range .Alerts,
    .Annotations, .StartsAt, .GeneratorURL, .ExternalURL.
  - Nối bằng `templates:` (nạp file) + `message: '{{ template "tên" . }}'` (gọi).
  - Nội dung tốt đến từ nguồn: annotation có runbook/dashboard, external_labels cho biết môi
    trường, --web.external-url để link bấm được.
  - HTML mode: tránh < > & trong annotation; giờ trong container là UTC.
  - Xem trước bằng `amtool template render`; gửi lỗi xem log + notifications_failed_total.
"""
print(__doc__)
