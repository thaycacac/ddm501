"""
Tự tính "request mỗi giây" từ Counter — đúng việc rate() của PromQL làm (bài 05).

Chạy (khi counter_demo.py đang chạy ở terminal khác):
    python scripts/manual_rate.py              # 2 lần lấy cách nhau 10 giây
    python scripts/manual_rate.py --seconds 30
"""
import argparse
import re
import time
from typing import Dict

import httpx

# Một dòng mẫu:  demo_requests_total{status="ok"} 412.0
# Nhóm 1 = tên + label (khóa nhận diện một time series), nhóm 2 = giá trị.
SAMPLE = re.compile(r"^(demo_requests_total(?:\{.*\})?)\s+([0-9.eE+-]+)$")


def scrape(url: str) -> Dict[str, float]:
    """Làm đúng việc của Prometheus trong một lần scrape: GET /metrics, đọc số."""
    values: Dict[str, float] = {}
    for line in httpx.get(url, timeout=5.0).text.splitlines():
        m = SAMPLE.match(line)
        if m:
            values[m.group(1)] = float(m.group(2))
    return values


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:28001/metrics")
    ap.add_argument("--seconds", type=int, default=10)
    args = ap.parse_args()

    first = scrape(args.url)
    t0 = time.time()
    print(f"lần 1: {first}")
    print(f"chờ {args.seconds} giây...")
    time.sleep(args.seconds)
    second = scrape(args.url)
    elapsed = time.time() - t0
    print(f"lần 2: {second}\n")

    # rate = (giá trị sau − giá trị trước) / số giây giữa hai lần.
    # Giá trị tuyệt đối (412, 47...) phụ thuộc process chạy bao lâu → vô nghĩa.
    # Hiệu số chia thời gian → "bao nhiêu mỗi giây NGAY LÚC NÀY" → có nghĩa.
    for series in sorted(second):
        before = first.get(series, 0.0)
        after = second[series]
        if after < before:
            # Counter chỉ tăng. Nếu thấy giảm → process đã restart, counter về 0.
            # rate() của Prometheus coi đoạn sau reset là tăng từ 0 lên `after`,
            # nên không bao giờ ra số âm. Ở đây ta làm y như vậy.
            print(f"  {series}: RESET phát hiện ({before} → {after})")
            delta = after
        else:
            delta = after - before
        print(f"  {series:<40} +{delta:>6.0f} trong {elapsed:4.1f}s  →  {delta / elapsed:5.2f} /giây")

    ok = second.get('demo_requests_total{status="ok"}', 0) - first.get('demo_requests_total{status="ok"}', 0)
    err = second.get('demo_requests_total{status="error"}', 0) - first.get('demo_requests_total{status="error"}', 0)
    if ok >= 0 and err >= 0 and ok + err > 0:
        # Tỉ lệ lỗi = lỗi / tổng, tính trên KHOẢNG THỜI GIAN, không phải trên tổng
        # tích lũy. Tutorial06 alert HighErrorRate dùng đúng công thức này (bài 05).
        print(f"\n  tỉ lệ lỗi trong {elapsed:.0f}s vừa qua: {err / (ok + err):.1%}")


if __name__ == "__main__":
    main()
