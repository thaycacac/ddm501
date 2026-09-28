"""
Đếm số time series service đang phơi ra trên /metrics
(= tutorial06/scripts/count_series.py, port mặc định 28000, thêm kích thước payload).

    python scripts/count_series.py
"""
import argparse
import collections
import re

import httpx

# Tên metric, rồi (tùy chọn) {label...}, rồi khoảng trắng. Mỗi dòng khớp = MỘT time series.
SAMPLE = re.compile(r"^([a-zA-Z_:][a-zA-Z0-9_:]*)(\{.*\})?\s")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:28000/metrics")
    ap.add_argument("--prefix", default="wdbc_")
    args = ap.parse_args()

    text = httpx.get(args.url, timeout=10.0).text
    by_name: collections.Counter = collections.Counter()
    for line in text.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        m = SAMPLE.match(line)
        if m and m.group(1).startswith(args.prefix):
            by_name[m.group(1)] += 1

    width = max((len(n) for n in by_name), default=10)
    for name, count in sorted(by_name.items()):
        print(f"  {name:<{width}}  {count:>6d}")
    print(f"\n  {'TOTAL':<{width}}  {sum(by_name.values()):>6d} time series")
    # Mỗi lần scrape (5s) Prometheus tải và phân tích toàn bộ trang này.
    print(f"  {'/metrics payload':<{width}}  {len(text.encode()):>6d} bytes")


if __name__ == "__main__":
    main()
