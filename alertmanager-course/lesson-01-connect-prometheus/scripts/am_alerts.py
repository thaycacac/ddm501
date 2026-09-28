"""
Hỏi Alertmanager đang giữ những alert nào (API v2) — giống lệnh curl trong tutorial07 README:
    curl -s http://localhost:9093/api/v2/alerts | python3 -m json.tool | grep alertname

    python3 scripts/am_alerts.py
"""
import argparse
import json
import urllib.request


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:29093")
    args = ap.parse_args()

    with urllib.request.urlopen(f"{args.url}/api/v2/alerts", timeout=5) as r:
        alerts = json.load(r)

    if not alerts:
        print("Alertmanager không giữ alert nào.")
        return

    for a in alerts:
        labels = a["labels"]
        # status.state: active (sẽ được gửi) | suppressed (bị silence/inhibit chặn, bài 03)
        state = a["status"]["state"]
        receivers = ",".join(r["name"] for r in a["receivers"])
        print(f"{labels.get('alertname'):<16} severity={labels.get('severity', '-'):<9} "
              f"state={state:<10} receivers={receivers:<14} startsAt={a['startsAt']}")
        # Khi alert còn cháy, Prometheus gửi kèm endsAt ≈ lúc gửi + 4 phút (4 × chu kỳ gửi lại 1m)
        # và gia hạn mỗi lần gửi lại. Prometheus chết, không gia hạn → quá endsAt thì Alertmanager
        # tự coi là resolved. (global.resolve_timeout chỉ dùng cho client KHÔNG gửi endsAt.)
        print(f"{'':<16} endsAt={a['endsAt']}  generatorURL={a.get('generatorURL', '-')}")
        # Bài 03: bị chặn vì ai? inhibitedBy = fingerprint của alert nguồn, silencedBy = id silence.
        if state == "suppressed":
            print(f"{'':<16} inhibitedBy={a['status']['inhibitedBy']}  "
                  f"silencedBy={a['status']['silencedBy']}")


if __name__ == "__main__":
    main()
