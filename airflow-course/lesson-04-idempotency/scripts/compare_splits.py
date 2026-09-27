"""
BÀI 04 — Hash split vs seeded shuffle khi nguồn thay đổi.

Chạy trong container:
  docker compose exec airflow python /opt/airflow/scripts/compare_splits.py

3 phiên bản của cùng một nguồn:
  original   orders.csv như hiện tại
  reordered  cùng 20 dòng, chỉ đổi THỨ TỰ
  extended   thêm 5 đơn hàng mới vào ĐẦU file
Với mỗi phiên bản, xem tập test (của 20 đơn cũ) có giữ nguyên không.
"""
import hashlib

import numpy as np
import pandas as pd

RAW = "/opt/airflow/data/raw/orders.csv"


def bucket(order_id: str) -> int:
    # Giống hệt hàm bucket trong dags/idempotent_pipeline.py
    return int(hashlib.sha256(order_id.encode()).hexdigest()[:8], 16) % 100


def hash_test(frame: pd.DataFrame) -> set:
    return set(frame.loc[frame["order_id"].map(bucket) < 20, "order_id"])


def seeded_test(frame: pd.DataFrame) -> set:
    # Cách hay gặp: random có seed cố định, lấy ~20% làm test
    rng = np.random.default_rng(42)
    mask = rng.random(len(frame)) < 0.20
    return set(frame.loc[mask, "order_id"])


original = pd.read_csv(RAW)
reordered = original.sample(frac=1, random_state=7)          # xáo thứ tự, không đổi nội dung
new_rows = pd.DataFrame({"order_id": [f"ORD-10{i}" for i in range(5)], "amount": 1.0})
extended = pd.concat([new_rows, original], ignore_index=True)  # thêm 5 dòng mới ở đầu

old_ids = set(original["order_id"])
base_hash, base_seed = hash_test(original), seeded_test(original)

print(f"{'phiên bản':<10} | {'hash: test của 20 đơn cũ':<34} | seeded: test của 20 đơn cũ")
for name, frame in (("original", original), ("reordered", reordered), ("extended", extended)):
    h = hash_test(frame) & old_ids
    s = seeded_test(frame) & old_ids
    h_note = "giữ nguyên" if h == base_hash else f"ĐỔI {len(h ^ base_hash)} id"
    s_note = "giữ nguyên" if s == base_seed else f"ĐỔI {len(s ^ base_seed)} id"
    print(f"{name:<10} | {str(sorted(h)):<22} {h_note:<11} | {sorted(s)} {s_note}")
