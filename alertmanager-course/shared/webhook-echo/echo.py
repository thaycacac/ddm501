"""
Receiver giả: nhận POST từ Alertmanager và in ra đúng những gì nó gửi.

Alertmanager có sẵn tích hợp `webhook_configs`: POST một JSON (version "4") tới URL bất kỳ.
Mọi tích hợp khác (Telegram, Slack, email) nhận CÙNG dữ liệu này, chỉ khác cách trình bày.
Nhìn payload thô trước thì bài template (05) sẽ dễ hiểu.

  POST /       nhận thông báo, in tóm tắt + JSON đầy đủ ra log
  GET  /       20 thông báo gần nhất (JSON)

Chỉ dùng thư viện chuẩn → chạy thẳng trong image python:3.11-slim, không cần build.
"""
import json
from collections import deque
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 5001
received: deque = deque(maxlen=20)


class Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        payload = json.loads(body or b"{}")
        received.append(payload)

        now = datetime.now().strftime("%H:%M:%S")
        # status của CẢ NHÓM: "firing" nếu còn ít nhất một alert đang cháy, "resolved" nếu tất cả đã hết.
        print(f"\n===== {now}  receiver={payload.get('receiver')}  "
              f"status={payload.get('status')}  alerts={len(payload.get('alerts', []))} =====")
        # groupLabels = các label dùng để gộp nhóm (group_by trong route).
        print(f"groupLabels: {payload.get('groupLabels')}")
        for a in payload.get("alerts", []):
            labels = a.get("labels", {})
            print(f"  - [{a.get('status')}] {labels.get('alertname')}  "
                  f"severity={labels.get('severity')}  startsAt={a.get('startsAt')}  "
                  f"endsAt={a.get('endsAt')}")
            print(f"      summary: {a.get('annotations', {}).get('summary')}")
        print(json.dumps(payload, indent=2, ensure_ascii=False), flush=True)

        self.send_response(200)
        self.end_headers()

    def do_GET(self) -> None:
        data = json.dumps(list(received), indent=2, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args) -> None:
        pass


if __name__ == "__main__":
    print(f"webhook-echo listening on :{PORT}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
