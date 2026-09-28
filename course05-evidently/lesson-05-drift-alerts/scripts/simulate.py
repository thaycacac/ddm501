"""
Vòng lặp "production giả": mỗi `--interval` giây gửi 100 mẫu vào /capture/batch rồi gọi /analyze.
Đóng vai simulations/ (gửi dữ liệu) + DAG drift_monitoring (phân tích theo lịch) của tutorial07.
Ctrl+C để dừng — gauge giữ giá trị lần cuối, DriftAnalysisStale sẽ bắn sau ~2.5 phút.

  ../.venv/bin/python scripts/simulate.py --scenario normal
  ../.venv/bin/python scripts/simulate.py --scenario moderate_drift
  ../.venv/bin/python scripts/simulate.py --scenario normal --missing alcohol:0.3 --missing pH:0.3
"""
import argparse
import importlib.util
import time
from datetime import datetime
from pathlib import Path

import httpx
import numpy as np

_path = Path(__file__).resolve().parents[2] / "lesson-02-report-data-drift" / "scripts" / "data.py"
_spec = importlib.util.spec_from_file_location("lesson02_data", _path)
_data = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_data)

p = argparse.ArgumentParser()
p.add_argument("--url", default="http://127.0.0.1:28101")
p.add_argument("--scenario", choices=list(_data.SCENARIOS), default="normal")
p.add_argument("--n", type=int, default=100, help="số mẫu mỗi vòng (= window_size)")
p.add_argument("--interval", type=float, default=20, help="giây giữa hai lần phân tích")
p.add_argument("--rounds", type=int, default=0, help="0 = chạy mãi tới khi Ctrl+C")
p.add_argument("--missing", action="append", default=[], metavar="COT:TYLE")
args = p.parse_args()

client = httpx.Client(base_url=args.url, timeout=60)

# reference chỉ cần nạp một lần (lưu trên volume, còn sau restart)
if not client.get("/reference").json().get("loaded"):
    ref = _data.make_batch(500, "normal", seed=1)
    client.post("/reference", json={"data": ref.to_dict("records"), "description": "500 normal"}).raise_for_status()
    print("Đã nạp reference 500 mẫu normal")

rng = np.random.default_rng()
i = 0
try:
    while args.rounds == 0 or i < args.rounds:
        i += 1
        rows = _data.make_batch(args.n, args.scenario, seed=int(rng.integers(2**31))).to_dict("records")
        for spec in args.missing:
            col, ratio = spec.split(":")
            for k in rng.choice(len(rows), size=int(float(ratio) * len(rows)), replace=False):
                rows[k][col] = None
        client.post("/capture/batch", json={"data": rows}).raise_for_status()

        r = client.post("/analyze", json={"window_size": args.n})
        stamp = datetime.now().strftime("%H:%M:%S")
        if r.status_code != 200:
            print(f"{stamp} vòng {i}: HTTP {r.status_code} {r.text}")
        else:
            res = r.json()
            miss = {f: v for f, v in res["missing_ratio"].items() if v > 0}
            print(f"{stamp} vòng {i} [{args.scenario}] drift={res['drift_detected']!s:<5}"
                  f" share={res['drift_score']:.2f} drifted={res['drifted_count']}/{res['total_features']}"
                  + (f" missing={miss}" if miss else ""))
        time.sleep(args.interval)
except KeyboardInterrupt:
    print("\nDừng gửi. Gauge vẫn giữ kết quả lần phân tích cuối — xem DriftAnalysisStale trên /alerts.")
