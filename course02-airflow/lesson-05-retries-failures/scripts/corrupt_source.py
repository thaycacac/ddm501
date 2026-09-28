"""
BÀI 05 — Làm hỏng nguồn để xem pipeline từ chối nó (= tutorial04/scripts/corrupt_extract.py).

Chạy trong container:
  docker compose exec airflow python /opt/airflow/scripts/corrupt_source.py           # xoá humidity ở 15% dòng
  docker compose exec airflow python /opt/airflow/scripts/corrupt_source.py --repair  # khôi phục bản gốc
"""
import argparse
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

RAW = Path("/opt/airflow/data/raw/readings.csv")
BACKUP = RAW.with_suffix(".csv.orig")     # bản gốc, giữ lại để --repair


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repair", action="store_true")
    ap.add_argument("--fraction", type=float, default=0.15)
    args = ap.parse_args()

    if args.repair:
        if BACKUP.exists():
            shutil.copy(BACKUP, RAW)
            print(f"restored {RAW.name} from {BACKUP.name}")
        else:
            print("no backup found; nothing to restore")
        return

    if not BACKUP.exists():
        shutil.copy(RAW, BACKUP)          # chỉ backup lần đầu → chạy corrupt 2 lần vẫn giữ bản gốc
        print(f"kept a copy at {BACKUP.name}")

    frame = pd.read_csv(RAW)
    n = int(len(frame) * args.fraction)
    hit = frame.sample(n, random_state=1).index
    frame.loc[hit, "humidity"] = np.nan   # xoá giá trị → lỗi "null"
    frame.to_csv(RAW, index=False)
    print(f"blanked humidity on {n} of {len(frame)} rows ({n / len(frame):.1%}) -- above the 5% limit")


if __name__ == "__main__":
    main()
