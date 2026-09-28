"""
BÀI 04 — Receiver Telegram
         (= tutorial07: service alertmanager trong docker-compose.yml dòng 270–291,
            receiver telegram trong alertmanager.yml dòng 33–41, scripts/test_telegram.sh)

1) Ba thứ cần có

   bot token   do BotFather cấp (nhắn /newbot cho @BotFather). Ai có token = điều khiển được bot
               → là BÍ MẬT, không commit.
   chat_id     nơi nhận tin. Thêm bot vào group, nhắn một tin trong group, rồi gọi getUpdates
               (test_telegram.py --chat-ids). Group: id âm; supergroup: -100...; group được
               nâng cấp lên supergroup thì id đổi → lỗi "chat not found".
   quyền       bot phải là thành viên group (và được phép gửi tin).

   Khóa này dùng lại bot + chat của tutorial07 (lấy từ ../tutorial07/.env).

2) Kiểm tra bot TRƯỚC, rồi mới giao cho Alertmanager

   test_telegram.py gọi thẳng Bot API sendMessage. Được → token và chat_id đúng.
   Không được mà cứ bật Alertmanager thì lỗi chỉ nằm trong log Alertmanager, khó thấy hơn.

3) Giữ bí mật đúng cách (giống tutorial07)

   token    → file secrets/telegram_bot_token (gitignore, quyền 600) → mount vào container
              → `bot_token_file:` trong config. Không nằm trong config, không trong env.
   chat_id  → biến môi trường TELEGRAM_CHAT_ID (không bí mật).
   Alertmanager không thay ${VAR} trong config → config là TEMPLATE có __TELEGRAM_CHAT_ID__,
   entrypoint chạy `sed` thay vào rồi ghi ra /tmp/alertmanager.yml, sau đó `exec` Alertmanager.
   Hệ quả: config THẬT nằm ở /tmp/alertmanager.yml → amtool check-config phải trỏ vào đó.

4) Một receiver, nhiều tích hợp

   receiver "telegram" có cả telegram_configs và webhook_configs → mỗi thông báo đi hai nơi.
   Cùng một payload (bài 01) → Telegram hiển thị bằng template mặc định telegram.default.message.
   Bài 05 thay bằng template riêng giống tutorial07.

5) Khi Telegram không nhận được tin — tìm theo thứ tự

   test_telegram.py có gửi được không?           → sai token / chat_id
     (CERTIFICATE_VERIFY_FAILED trên macOS: Python cài từ python.org chưa có bộ CA → chạy
      "Install Certificates.command" trong /Applications/Python 3.x, hoặc dùng SSL_CERT_FILE)
   docker compose exec alertmanager cat /tmp/alertmanager.yml | grep chat_id
                                                 → chat_id có bị rỗng không (quên --env-file)
   docker compose logs alertmanager | grep -i telegram
                                                 → lỗi gửi (chat not found, unauthorized...)
   Metric: alertmanager_notifications_failed_total{integration="telegram"} trên Prometheus.

File:
  scripts/test_telegram.py       gửi tin thử, --chat-ids, ghi secrets/telegram_bot_token
  alertmanager/alertmanager.yml  TEMPLATE config, receiver telegram + webhook-echo
  docker-compose.yml             entrypoint sed + bot_token_file + TELEGRAM_CHAT_ID

TỔNG KẾT
  - Telegram cần token (bí mật, từ BotFather), chat_id (getUpdates), bot nằm trong group.
  - Kiểm tra bằng Bot API trực tiếp trước khi giao cho Alertmanager.
  - Token qua bot_token_file (file mount, gitignore); chat_id qua env + sed vì Alertmanager
    không thay biến môi trường trong config.
  - Một receiver có thể gửi nhiều kênh cùng lúc (telegram_configs + webhook_configs).
  - Không nhận được tin: test_telegram → chat_id trong /tmp/alertmanager.yml → log Alertmanager
    → alertmanager_notifications_failed_total.
"""
print(__doc__)
