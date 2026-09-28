# Khóa thực hành: Alertmanager → phần cảnh báo của Tutorial 07

Mục tiêu cuối: đọc và giải thích được **từng dòng** phần cảnh báo của `../tutorial07`:
`config/prometheus.yml` (khối `alerting:`), `config/alertmanager/alertmanager.yml`,
`config/alertmanager/templates/telegram.tmpl`, service `alertmanager` trong `docker-compose.yml`
và `scripts/test_telegram.sh`.

Vì sao cần: khóa Prometheus dừng ở chỗ alert chuyển sang **firing** — thấy trên trang `/alerts`
nhưng không ai được báo. Alertmanager nhận alert từ Prometheus rồi quyết định **gửi cho ai, gộp
thế nào, bao lâu nhắc lại, khi nào im lặng**, và gửi thật (Telegram, email, Slack, webhook...).

## Lộ trình tổng (3 khóa)

```
prometheus-course (xong) → alertmanager-course → evidently-course → airflow-course 05–10 → Capstone T07
```

| Khóa | Nội dung chính | Ánh xạ vào tutorial07 |
|------|----------------|------------------------|
| **alertmanager-course** (khóa này) | route, group, inhibit, silence, Telegram, template | `config/alertmanager/**`, service `alertmanager` |
| evidently-course | kiểm định drift, Report, TestSuite, Evidently thành service, alert drift | `evidently/main.py`, `config/prometheus/evidently_alerts.yml` |
| airflow-course 06–10 | branch, Params, trigger DAG, callback, LocalExecutor + Postgres, StatsD, DAG train lại | `airflow_dags/**`, `airflow/**`, `config/statsd_mapping.yml` |
| Capstone T07 | chạy toàn bộ stack, tái hiện bảng Evidence, sửa alert hỏng | toàn bộ `../tutorial07` (ghi trong README của airflow-course) |

## Ports

| Service | Port khóa học | Ghi chú |
|---------|---------------|---------|
| API FastAPI (WDBC) | 28000 | dùng lại app của `prometheus-course/lesson-03` |
| Prometheus | 29090 | như khóa Prometheus |
| Alertmanager | 29093 | UI + API `/api/v2/...` |
| webhook-echo | 25001 | receiver giả: in ra đúng JSON Alertmanager gửi |

Cùng port với khóa Prometheus → **tắt stack `prometheus-course` trước** khi bật khóa này.

## Quy ước mỗi bài

- Thư mục `lesson-NN-<chủ-đề>/`, có `READ_WITH_ME.py` (lý thuyết + danh sách file + ánh xạ vào
  tutorial07), kết thúc bằng mục **TỔNG KẾT**. Không có câu hỏi/bài làm.
- Lý thuyết nằm ngay trong comment của file cấu hình. **Mọi comment viết bằng tiếng Việt.**
- Docker Compose `name: alertmanager-course-NN`, container `alertmanager-course-NN-<service>`.
- API build từ `../prometheus-course` (không copy code). Script Python dùng venv của khóa
  Prometheus: `../prometheus-course/.venv/bin/python`.
- `shared/webhook-echo/echo.py`: receiver giả dùng chung mọi bài (chỉ thư viện chuẩn).
- Telegram (từ bài 04): dùng lại bot/chat của tutorial07. `cp .env.example .env` rồi điền
  `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`. `.env` và `secrets/` nằm trong `.gitignore`.
- Mỗi bài chỉ được tạo khi bạn học xong bài trước; mỗi bước hướng dẫn trên chat.
- **Bạn tự chạy mọi lệnh** (docker, script, curl). Lỗi gì thì báo lại để cùng phân tích.

## Roadmap

| Bài | Chủ đề | Ánh xạ vào tutorial07 | Status |
|-----|--------|------------------------|--------|
| 01 | Nối Prometheus → Alertmanager → webhook; vòng đời alert; payload; `amtool`; API v2 | `config/prometheus.yml` dòng 14–19 | Xong |
| 02 | Routing và grouping: cây `route`, `group_by`, `group_wait` / `group_interval` / `repeat_interval`, `matchers`, `continue` | `alertmanager.yml` dòng 13–23 | Xong |
| 03 | Inhibition và silence | `alertmanager.yml` dòng 25–31 | Xong |
| 04 | Receiver Telegram: BotFather, `chat_id`, `telegram_configs`, `bot_token_file`, mẹo `sed` | `docker-compose.yml` dòng 270–291, `scripts/test_telegram.sh` | Xong |
| 05 | Template tin nhắn (Go template), `external_labels`, annotation runbook/dashboard | `templates/telegram.tmpl` | Xong |

## Trạng thái

Khóa đã xong. Học tiếp ở `../evidently-course`.
