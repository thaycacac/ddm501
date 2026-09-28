"""
Bắn request vào API — 569 dòng nằm trong file không vẽ ra biểu đồ nào.
(= tutorial06/scripts/traffic.py, đổi port mặc định thành 28000)

  python scripts/traffic.py                      # đều đặn, dữ liệu bình thường
  python scripts/traffic.py --broken 0.2         # 20% request thiếu field
  python scripts/traffic.py --drift 3.0          # dịch mọi feature thêm 3 độ lệch chuẩn
  python scripts/traffic.py --rps 40 --seconds 60
"""
import argparse
import json
import random
import time
from pathlib import Path

import httpx
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "wdbc.csv"
CARD = ROOT / "models" / "model_card.json"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:28000")
    ap.add_argument("--rps", type=float, default=10.0)
    ap.add_argument("--seconds", type=int, default=120)
    ap.add_argument("--drift", type=float, default=0.0,
                    help="cộng N độ lệch chuẩn vào mọi feature")
    ap.add_argument("--broken", type=float, default=0.0,
                    help="tỉ lệ request bị bỏ một field bắt buộc")
    args = ap.parse_args()

    features = json.loads(CARD.read_text())["features"]
    frame = pd.read_csv(RAW).dropna().drop_duplicates("sample_id")
    stds = frame[features].std()

    sent = ok = failed = 0
    deadline = time.time() + args.seconds
    interval = 1.0 / args.rps
    with httpx.Client(timeout=5.0) as client:
        while time.time() < deadline:
            row = frame.sample(1).iloc[0]
            # --drift: mọi feature lớn lên N độ lệch chuẩn → "dân số" bệnh nhân khác
            # hẳn lúc train. Request vẫn hợp lệ, API vẫn trả 200 — không có lỗi nào.
            values = {f: float(row[f]) + args.drift * float(stds[f]) for f in features}
            if args.broken and random.random() < args.broken:
                values.pop(features[0])          # bỏ một field API bắt buộc → 422
            try:
                r = client.post(f"{args.url}/predict",
                                json={"sample_id": row["sample_id"], "features": values})
                ok += r.status_code == 200
                failed += r.status_code != 200
            except httpx.HTTPError:
                failed += 1
            sent += 1
            if sent % 50 == 0:
                print(f"  sent {sent}  ok {ok}  failed {failed}")
            time.sleep(interval)

    print(f"\ndone: {sent} requests, {ok} ok, {failed} failed")


if __name__ == "__main__":
    main()
