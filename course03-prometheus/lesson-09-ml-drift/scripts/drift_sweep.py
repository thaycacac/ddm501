"""
Quét nhiều mức drift: mỗi mức bắn 250 request (> cửa sổ 200 của deque, để cửa sổ chỉ
còn dữ liệu của mức đó), rồi đọc wdbc_malignant_share từ /metrics.

Chạy (khi stack bài 08 đang chạy):
    python scripts/drift_sweep.py
    python scripts/drift_sweep.py --levels -2 -1 0 1 2
"""
import argparse
import json
import math
import re
from pathlib import Path

import httpx
import pandas as pd

LESSON03 = Path(__file__).resolve().parents[2] / "lesson-03-instrument-fastapi"
RAW = LESSON03 / "data" / "raw" / "wdbc.csv"
CARD = LESSON03 / "models" / "model_card.json"

BASELINE = 0.37      # = expr của alert MalignantShareShift
THRESHOLD = 0.15
WINDOW = 200
SHARE = re.compile(r"^wdbc_malignant_share\s+(\S+)$", re.M)


def send_batch(client: httpx.Client, url: str, frame: pd.DataFrame, features, stds,
               drift: float, n: int) -> None:
    for _ in range(n):
        row = frame.sample(1).iloc[0]
        # Cộng drift × độ lệch chuẩn vào MỌI feature: dữ liệu vẫn hợp lệ, API vẫn trả 200.
        values = {f: float(row[f]) + drift * float(stds[f]) for f in features}
        client.post(f"{url}/predict", json={"sample_id": row["sample_id"], "features": values})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:28000")
    ap.add_argument("--levels", type=float, nargs="+", default=[-3, -1.5, 0, 0.5, 1.5, 3])
    ap.add_argument("--per-level", type=int, default=250)
    args = ap.parse_args()

    features = json.loads(CARD.read_text())["features"]
    frame = pd.read_csv(RAW).dropna().drop_duplicates("sample_id")
    stds = frame[features].std()

    sigma = math.sqrt(BASELINE * (1 - BASELINE) / WINDOW)
    print(f"baseline {BASELINE:.2f}, ngưỡng ±{THRESHOLD:.2f}, "
          f"nhiễu 1σ của tỉ lệ trên {WINDOW} mẫu ≈ {sigma:.3f} → ngưỡng ≈ {THRESHOLD / sigma:.1f}σ\n")
    print(f"  {'drift':>6}   {'share':>6}   {'lệch':>6}   biểu đồ (| = baseline)            alert?")

    with httpx.Client(timeout=5.0) as client:
        for drift in args.levels:
            send_batch(client, args.url, frame, features, stds, drift, args.per_level)
            share = float(SHARE.search(client.get(f"{args.url}/metrics").text).group(1))
            gap = abs(share - BASELINE)
            bar = [" "] * 31
            bar[round(BASELINE * 30)] = "|"
            bar[round(share * 30)] = "●"
            fires = "CÓ (sau for:)" if gap > THRESHOLD else "không"
            print(f"  {drift:>+6.1f}   {share:6.3f}   {gap:6.3f}   [{''.join(bar)}]   {fires}")

    print("\nMọi request ở trên đều trả 200: error share = 0, latency bình thường.")


if __name__ == "__main__":
    main()
