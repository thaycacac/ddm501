# =============================================================================
# BÀI 03 — app ghi file vào /data và phục vụ HTTP (để chứng minh VOLUME)
# =============================================================================
#
# Khi bind-mount ./data-on-host:/data :
#   - File viết vào /data trong container → xuất hiện trên máy bạn
#   - docker compose down XÓA container nhưng KHÔNG xóa ./data-on-host
# → Đúng pattern Tutorial 02: ./mlflow-data sống sau khi down.
# =============================================================================

from __future__ import annotations

import json
import os
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

DATA = Path(os.environ.get("DATA_DIR", "/data"))
PORT = int(os.environ.get("PORT", "8000"))


def ensure_log() -> Path:
    DATA.mkdir(parents=True, exist_ok=True)
    log = DATA / "visits.log"
    if not log.exists():
        log.write_text("lesson-03 ready\n", encoding="utf-8")
    return log


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        log = ensure_log()
        if self.path.startswith("/health"):
            body = b"ok"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} hit {self.path}\n"
        with log.open("a", encoding="utf-8") as f:
            f.write(line)

        payload = {
            "lesson": 3,
            "data_dir": str(DATA),
            "log_tail": log.read_text(encoding="utf-8").strip().splitlines()[-5:],
        }
        body = json.dumps(payload, indent=2).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:
        print(f"[app] {fmt % args}", flush=True)


def main() -> None:
    ensure_log()
    print(f"[app] DATA_DIR={DATA} PORT={PORT}", flush=True)
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
