"""
BÀI 01 — Nối Prometheus với Alertmanager
         (= tutorial07: config/prometheus.yml dòng 14–19, service alertmanager trong
            docker-compose.yml dòng 270–291 — phần Telegram để bài 04)

1) Vì sao cần Alertmanager

   Prometheus biết alert nào đang firing, nhưng KHÔNG gửi tin cho ai cả. Nếu mỗi rule tự
   gửi tin thì: API chết → ApiDown + HighErrorRate + SlowPredictions cùng bắn, mỗi cái
   nhắn lại mỗi 5 giây, lúc 3 giờ sáng. Alertmanager đứng giữa và lo 4 việc:
     gộp nhóm (group)     nhiều alert liên quan → một tin nhắn           (bài 02)
     định tuyến (route)   critical → kênh trực, warning → kênh chat      (bài 02)
     chặn (inhibit)       có critical thì không gửi warning cùng loại    (bài 03)
     im lặng (silence)    đang bảo trì → tắt tạm theo label              (bài 03)
   rồi gửi qua receiver: webhook, Telegram, email, Slack...              (bài 04–05)

2) Đường đi của một alert

   api ──scrape (pull)──► Prometheus ──đánh giá rule mỗi 5s──► pending ──(for: 30s)──► firing
                                                                                        │
                           POST /api/v2/alerts (push, chỉ alert FIRING) ◄───────────────┘
                                         │
                                   Alertmanager: gộp nhóm, đợi group_wait (10s)
                                         │
                                   receiver webhook-echo: POST JSON

   - Prometheus gửi lại alert đang cháy khoảng mỗi 1 phút (để Alertmanager biết nó còn cháy).
   - Khi expr hết đúng, Prometheus gửi lần cuối kèm endsAt → Alertmanager đánh dấu resolved
     và (vì send_resolved: true) gửi thêm một tin "đã hết".
   - Trong payload, alert đang firing có endsAt = "0001-01-01T00:00:00Z" (chưa biết khi nào hết);
     alert resolved có endsAt thật.
   - Thời gian đo được khi tắt API: ~30s (for) + ~5s (scrape) + 10s (group_wait) ≈ 45s mới có tin.
   - Cấu hình phía Prometheus chỉ có khối `alerting:` trỏ tới alertmanager:9093.
     Mọi quyết định "gửi cho ai" nằm ở alertmanager.yml.

3) Payload webhook (cái mọi receiver đều nhận, chỉ khác cách trình bày)

   {
     "receiver": "webhook-echo",
     "status": "firing",                     ← của CẢ NHÓM
     "groupLabels":  {"alertname": "ApiDown"}, ← label dùng để gộp (group_by)
     "commonLabels": {...},                  ← label mọi alert trong nhóm đều có
     "commonAnnotations": {...},
     "alerts": [ {"status", "labels", "annotations", "startsAt", "endsAt",
                  "generatorURL", "fingerprint"} , ... ],
     "groupKey": "...", "externalURL": "...", "version": "4"
   }
   Bài 05 viết template Telegram chính là đọc các trường này: .Status, .CommonLabels, .Alerts.

4) Alertmanager không chỉ nhận từ Prometheus

   Ai POST đúng định dạng vào /api/v2/alerts cũng được: `amtool alert add`, script, service khác.
   amtool = CLI đi kèm image Alertmanager: kiểm tra config, xem/thêm alert, tạo silence.
   Alert thêm bằng amtool không có endsAt → Alertmanager tự đặt endsAt = lúc nhận +
   global.resolve_timeout (mặc định 5m) → sau 5 phút tự resolved.

File:
  docker-compose.yml             api + prometheus + alertmanager + webhook-echo
  prometheus/prometheus.yml      khối alerting:, job scrape alertmanager
  prometheus/alerts/api.yml      ApiDown (critical), HighErrorRate (warning)
  alertmanager/alertmanager.yml  route tối thiểu → một receiver webhook
  ../shared/webhook-echo/echo.py receiver giả, in payload
  scripts/am_alerts.py           gọi GET /api/v2/alerts

TỔNG KẾT
  - Prometheus ĐÁNH GIÁ rule; Alertmanager QUYẾT ĐỊNH gửi cho ai, gộp thế nào, khi nào im lặng.
  - Nối hai bên bằng khối `alerting.alertmanagers` trong prometheus.yml. Prometheus push
    alert FIRING (không gửi pending), gửi lại ~mỗi phút, gửi endsAt khi hết.
  - alertmanager.yml tối thiểu = route (receiver mặc định + group_by + 3 mốc thời gian)
    + receivers. send_resolved: true → có thêm tin "resolved".
  - Mọi receiver nhận cùng một payload: status, groupLabels, commonLabels, alerts[].
  - Kiểm tra: UI :29093, GET /api/v2/alerts, amtool check-config, amtool alert add.
"""
print(__doc__)
