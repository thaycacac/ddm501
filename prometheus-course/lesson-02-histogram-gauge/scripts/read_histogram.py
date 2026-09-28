"""
Đọc histogram từ /metrics, tính trung bình và TỰ ước lượng percentile từ bucket
— cùng thuật toán với histogram_quantile() của PromQL (bài 06).

Chạy (khi latency_demo.py đang chạy):
    python scripts/read_histogram.py
"""
import argparse
import math
import re
from collections import defaultdict
from typing import Dict, List, Tuple

import httpx

METRIC = "demo_latency_seconds"
BUCKET = re.compile(rf'^{METRIC}_bucket\{{le="([^"]+)",system="([^"]+)"\}}\s+(\S+)$')
SUM_COUNT = re.compile(rf'^{METRIC}_(sum|count)\{{system="([^"]+)"\}}\s+(\S+)$')
GAUGE = re.compile(r"^(demo_queue_depth|demo_model_loaded|demo_model_info)(\{.*\})?\s+(\S+)$")


def estimate_quantile(q: float, buckets: List[Tuple[float, float]]) -> float:
    """
    buckets: [(le, số_đếm_cộng_dồn), ...] đã sắp theo le tăng dần, phần tử cuối là +Inf.

    1. rank = q * tổng số request   (vd p95 của 1000 request → request thứ 950)
    2. tìm bucket ĐẦU TIÊN có số cộng dồn >= rank
    3. giả định request phân bố ĐỀU trong bucket đó → nội suy tuyến tính
       giữa mép dưới (le của bucket trước) và mép trên (le của bucket này)
    Giả định "phân bố đều" chính là nguồn sai số: bucket càng rộng, ước lượng càng thô.
    """
    total = buckets[-1][1]
    if total == 0:
        return float("nan")
    rank = q * total
    prev_le, prev_count = 0.0, 0.0
    for le, count in buckets:
        if count >= rank:
            if math.isinf(le):
                # Rơi vào +Inf: không có mép trên để nội suy → trả về bucket hữu hạn
                # lớn nhất. Đây là lý do "p95 trên 1 s đọc thành đúng 1 s".
                return prev_le
            if count == prev_count:
                return le
            return prev_le + (le - prev_le) * (rank - prev_count) / (count - prev_count)
        prev_le, prev_count = le, count
    return prev_le


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:28001/metrics")
    args = ap.parse_args()

    text = httpx.get(args.url, timeout=5.0).text
    buckets: Dict[str, List[Tuple[float, float]]] = defaultdict(list)
    sums: Dict[str, Dict[str, float]] = defaultdict(dict)
    gauges: List[str] = []

    for line in text.splitlines():
        if m := BUCKET.match(line):
            buckets[m.group(2)].append((float(m.group(1)), float(m.group(3))))
        elif m := SUM_COUNT.match(line):
            sums[m.group(2)][m.group(1)] = float(m.group(3))
        elif m := GAUGE.match(line):
            gauges.append(f"{m.group(1)}{m.group(2) or ''} = {m.group(3)}")

    for system in sorted(buckets):
        bs = sorted(buckets[system])
        total = bs[-1][1]
        print(f"\n=== system={system}   ({total:.0f} request) ===")
        print("  le (giây)     cộng dồn     % request <= le")
        for le, count in bs:
            label = "+Inf" if math.isinf(le) else f"{le:g}"
            print(f"  {label:<10} {count:>10.0f}     {count / total:6.1%}")

        # Trung bình = _sum / _count. Hai hệ thống sẽ ra gần như bằng nhau.
        avg = sums[system]["sum"] / sums[system]["count"]
        print(f"\n  trung bình (_sum/_count): {avg * 1000:7.1f} ms")
        for q in (0.5, 0.95, 0.99):
            print(f"  p{int(q * 100):<2} ước lượng từ bucket:  {estimate_quantile(q, bs) * 1000:7.1f} ms")

    print("\n=== gauge ===")
    for g in gauges:
        print(f"  {g}")


if __name__ == "__main__":
    main()
