"""
Bắn alert giả thẳng vào Alertmanager (POST /api/v2/alerts) — làm đúng việc Prometheus làm,
nhưng chủ động được label và thời điểm, để thí nghiệm route/group mà không phải chờ rule.

  python3 scripts/fire.py DiskFull severity=warning component=api
  python3 scripts/fire.py A,B,C severity=warning component=api        # 3 alert cùng lúc
  python3 scripts/fire.py DiskFull severity=warning component=api --resolve

Chỉ dùng thư viện chuẩn.
"""
import argparse
import json
import urllib.request
from datetime import datetime, timedelta, timezone


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("names", help="alertname, nhiều tên cách nhau bằng dấu phẩy")
    ap.add_argument("labels", nargs="*", help="label=value")
    ap.add_argument("--resolve", action="store_true", help="báo alert đã hết (endsAt = bây giờ)")
    ap.add_argument("--url", default="http://127.0.0.1:29093")
    args = ap.parse_args()

    extra = dict(pair.split("=", 1) for pair in args.labels)
    now = datetime.now(timezone.utc)
    # Firing: endsAt ở tương lai (10 phút) → alert sống đủ lâu để quan sát repeat_interval.
    # Prometheus cũng làm y hệt: gửi endsAt ở tương lai rồi gia hạn mỗi lần gửi lại.
    # Resolved: endsAt = bây giờ → Alertmanager coi là đã hết ngay.
    ends = now if args.resolve else now + timedelta(minutes=10)

    alerts = []
    for name in args.names.split(","):
        alerts.append({
            # Alertmanager nhận diện "cùng một alert" bằng TOÀN BỘ label (fingerprint).
            # Gửi lại cùng label = cập nhật alert cũ; đổi một label = alert mới.
            "labels": {"alertname": name, **extra},
            "annotations": {"summary": f"{name} (bắn bằng fire.py)"},
            "startsAt": now.isoformat(),
            "endsAt": ends.isoformat(),
        })

    req = urllib.request.Request(
        f"{args.url}/api/v2/alerts",
        data=json.dumps(alerts).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    urllib.request.urlopen(req, timeout=5)
    state = "resolved" if args.resolve else "firing"
    print(f"{now:%H:%M:%S}  sent {len(alerts)} {state}: {args.names}  {extra}")


if __name__ == "__main__":
    main()
