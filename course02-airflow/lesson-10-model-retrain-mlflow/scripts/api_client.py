"""
BÀI 10 — Gọi API model từ máy (thư viện chuẩn, không cần venv).

  python3 scripts/api_client.py health
  python3 scripts/api_client.py info
  python3 scripts/api_client.py predict      gửi 1 mẫu load_wine (lớp 0)
  python3 scripts/api_client.py reload       tự gọi /model/reload như task reload_api
"""
import json
import sys
import urllib.error
import urllib.request

API = "http://127.0.0.1:28000"
# Hàng đầu tiên của sklearn load_wine (13 feature: alcohol, malic_acid, ash, ..., proline) → lớp 0
SAMPLE = [14.23, 1.71, 2.43, 15.6, 127.0, 2.8, 3.06, 0.28, 2.29, 5.64, 1.04, 3.92, 1065.0]


def call(method: str, path: str, body: dict = None) -> None:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(API + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            print(resp.status, json.dumps(json.loads(resp.read()), indent=2, ensure_ascii=False))
    except urllib.error.HTTPError as exc:
        print(exc.code, exc.read().decode())


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "health"
    if cmd == "health":
        call("GET", "/health")
    elif cmd == "info":
        call("GET", "/model/info")
    elif cmd == "predict":
        call("POST", "/predict", {"features": SAMPLE})
    elif cmd == "reload":
        call("POST", "/model/reload")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
