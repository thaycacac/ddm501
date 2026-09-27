# Lesson 02 — HTTP app nhỏ để chứng minh: image BẠN build chạy được.
#
# Chạy trong container bởi CMD ["python", "app.py"].
# PORT lấy từ ENV (Dockerfile set PORT=8000; có thể -e PORT=... lúc run).
#
# Bind 0.0.0.0: nhận traffic từ bên ngoài container khi host dùng -p.
# Nếu listen 127.0.0.1 thì chỉ process trong container gọi được — -p vô dụng.

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        body = json.dumps(
            {
                "lesson": 2,
                "message": "image built from YOUR Dockerfile",
                "port": int(os.environ.get("PORT", "8000")),
            }
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:
        print(f"[app] {self.address_string()} {fmt % args}")


def main() -> None:
    port = int(os.environ.get("PORT", "8000"))
    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"[app] listening on 0.0.0.0:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
