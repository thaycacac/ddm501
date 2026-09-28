"""
Client gọi Evidently service — đóng vai simulations/ và DAG drift_monitoring của tutorial07.

  ../.venv/bin/python scripts/client.py health
  ../.venv/bin/python scripts/client.py reference --n 500
  ../.venv/bin/python scripts/client.py capture --n 100 --scenario moderate_drift [--missing alcohol:0.3]
  ../.venv/bin/python scripts/client.py analyze [--window 100] [--threshold 0.3] [--stattest-threshold 0.01]
  ../.venv/bin/python scripts/client.py metrics
  ../.venv/bin/python scripts/client.py reset
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

import httpx
import numpy as np

# nạp bộ sinh dữ liệu của bài 02 (cùng tên data.py nên nạp theo đường dẫn)
_path = Path(__file__).resolve().parents[2] / "lesson-02-report-data-drift" / "scripts" / "data.py"
_spec = importlib.util.spec_from_file_location("lesson02_data", _path)
_data = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_data)

p = argparse.ArgumentParser()
p.add_argument("--url", default="http://127.0.0.1:28101")
sub = p.add_subparsers(dest="cmd", required=True)
sub.add_parser("health")
r = sub.add_parser("reference")
r.add_argument("--n", type=int, default=500)
r.add_argument("--seed", type=int, default=1)
c = sub.add_parser("capture")
c.add_argument("--n", type=int, default=100)
c.add_argument("--scenario", choices=list(_data.SCENARIOS), default="normal")
c.add_argument("--seed", type=int, default=None, help="bỏ trống → mỗi lần một dữ liệu khác")
c.add_argument("--missing", action="append", default=[], metavar="COT:TYLE",
               help="vd alcohol:0.3 → 30%% dòng gửi alcohol=null")
a = sub.add_parser("analyze")
a.add_argument("--window", type=int)
a.add_argument("--threshold", type=float, help="drift_share: tỷ lệ cột drift để coi dataset drift")
a.add_argument("--stattest-threshold", type=float, help="ngưỡng của từng kiểm định")
sub.add_parser("metrics")
sub.add_parser("reset")
args = p.parse_args()

client = httpx.Client(base_url=args.url, timeout=60)


def show(resp: httpx.Response):
    if resp.status_code >= 400:
        print(f"HTTP {resp.status_code}: {resp.text}")
        sys.exit(1)
    return resp.json()


if args.cmd == "health":
    print(json.dumps(show(client.get("/health")), indent=2, ensure_ascii=False))

elif args.cmd == "reference":
    df = _data.make_batch(args.n, "normal", seed=args.seed)
    body = {"data": df.to_dict("records"), "feature_names": list(df.columns),
            "description": f"{args.n} mẫu normal, seed={args.seed}"}
    print(show(client.post("/reference", json=body)))

elif args.cmd == "capture":
    seed = args.seed if args.seed is not None else int(np.random.SeedSequence().entropy % 2**32)
    df = _data.make_batch(args.n, args.scenario, seed=seed)
    rows = df.to_dict("records")
    rng = np.random.default_rng(seed)
    for spec in args.missing:
        col, ratio = spec.split(":")
        for i in rng.choice(len(rows), size=int(float(ratio) * len(rows)), replace=False):
            rows[i][col] = None     # JSON null → NaN trong DataFrame của service
    # tutorial07 simulations gửi từng mẫu qua /capture; ở đây gửi batch cho nhanh
    print(show(client.post("/capture/batch", json={"data": rows})))

elif args.cmd == "analyze":
    body = {k: v for k, v in {"window_size": args.window, "threshold": args.threshold,
                              "stattest_threshold": args.stattest_threshold}.items() if v is not None}
    res = show(client.post("/analyze", json=body))
    print(f"drift_detected={res['drift_detected']}  drift_score(share)={res['drift_score']:.2f}"
          f"  drift_share={res['drift_share']}  drifted={res['drifted_count']}/{res['total_features']}"
          f"  ({res['current_samples']} vs {res['reference_samples']} mẫu, {res['duration_seconds']}s)")
    print(f"{'feature':<22} {'stattest':<24} {'score':>10} {'drift':>6} {'missing':>8}")
    for f, score in sorted(res["drift_scores"].items()):
        print(f"{f:<22} {res['stattests'][f]:<24} {score:>10.4g} {str(f in res['drifted_features']):>6}"
              f" {res['missing_ratio'].get(f, 0):>8.2f}")
    print(f"report: {args.url}{res['report_url']}")

elif args.cmd == "metrics":
    text = client.get("/metrics").text
    for line in text.splitlines():
        # chỉ in mẫu evidently_*, bỏ dòng # HELP/# TYPE và metric mặc định của python/process
        if line.startswith("evidently_") and "_bucket" not in line:
            print(line)

elif args.cmd == "reset":
    print(show(client.delete("/production-data")))
