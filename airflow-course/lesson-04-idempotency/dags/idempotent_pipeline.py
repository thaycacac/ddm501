"""
BÀI 04 — Pipeline idempotent (cùng kỹ thuật với tutorial04/wdbc_pipeline.py).

  ingest ─► split ─► report
                 └─► report_naive   (cố ý KHÔNG idempotent, để so sánh)

Output của mỗi ngày nằm trong data/staging/<ds>/.
Log chung: data/staging/history.jsonl (idempotent) và history_naive.jsonl (không).
"""
from __future__ import annotations

import hashlib            # sha256 cho hash split
import json
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd       # có trong image airflow-course:2.8.4 (bài 01)
from airflow.decorators import dag, task

log = logging.getLogger(__name__)

PROJECT = Path(__file__).resolve().parents[1]        # /opt/airflow
RAW = PROJECT / "data" / "raw" / "orders.csv"        # nguồn (có thể đổi bất cứ lúc nào)
STAGING = PROJECT / "data" / "staging"               # output của pipeline
TEST_FRACTION = 0.20                                 # ~20% đơn hàng vào tập test


def run_dir(ds: str) -> Path:
    """Thư mục riêng của một ngày (= tutorial04 dòng 30–35).

    Chạy lại ngày ds chỉ ghi đè thư mục này, không đụng ngày khác.
    """
    d = STAGING / ds                       # ví dụ data/staging/2026-09-25
    d.mkdir(parents=True, exist_ok=True)   # exist_ok: chạy lại không lỗi vì thư mục đã có
    return d


def bucket(order_id: str) -> int:
    """Biến id thành một số 0–99, cố định mãi mãi cho cùng một id (= tutorial04 dòng 117–119)."""
    digest = hashlib.sha256(order_id.encode()).hexdigest()  # hash hex 64 ký tự
    return int(digest[:8], 16) % 100       # lấy 8 ký tự đầu → số nguyên → chia dư 100


@dag(
    dag_id="lesson04_idempotent",
    schedule="@daily",
    start_date=datetime(2026, 9, 20),
    catchup=False,                         # giống tutorial04: không tự chạy bù, dùng backfill
    max_active_runs=1,                     # các ngày chạy lần lượt → history.jsonl không bị ghi đồng thời
    tags=["airflow-course", "lesson-04"],
)
def lesson04_idempotent():

    @task
    def ingest(ds: str = None) -> dict:
        # Đọc nguồn MỘT lần duy nhất trong cả run...
        frame = pd.read_csv(RAW)
        out = run_dir(ds) / "raw.parquet"
        # ...và "đóng băng" vào thư mục của ngày. Task sau chỉ đọc file này.
        frame.to_parquet(out, index=False)
        log.info("ingested %d rows → %s", len(frame), out)
        return {"rows": len(frame), "path": str(out)}   # XCom: chỉ số đếm + đường dẫn

    @task
    def split(meta: dict, ds: str = None) -> dict:
        frame = pd.read_parquet(meta["path"])            # đọc snapshot, KHÔNG đọc lại CSV
        # Mỗi dòng vào test nếu bucket(id) < 20 — không có random, không phụ thuộc thứ tự dòng
        is_test = frame["order_id"].map(bucket) < TEST_FRACTION * 100
        frame[~is_test].to_parquet(run_dir(ds) / "train.parquet", index=False)
        frame[is_test].to_parquet(run_dir(ds) / "test.parquet", index=False)
        log.info("split: %d train / %d test", (~is_test).sum(), is_test.sum())
        # int(...) vì numpy int64 không serialize được sang XCom JSON
        return {"train": int((~is_test).sum()), "test": int(is_test.sum())}

    @task
    def report(meta: dict, split_info: dict, ds: str = None) -> str:
        summary = {"ds": ds, "rows": meta["rows"], **split_info}
        (run_dir(ds) / "summary.json").write_text(json.dumps(summary, indent=2))

        line = json.dumps(summary, sort_keys=True)       # sort_keys → cùng dữ liệu = cùng chuỗi
        history = STAGING / "history.jsonl"
        # Đọc lại toàn bộ file, BỎ dòng cũ của chính ngày ds (= tutorial04 dòng 153–156)
        old = history.read_text().splitlines() if history.exists() else []
        kept = [l for l in old if json.loads(l).get("ds") != ds]
        # Ghi lại cả file: các ngày khác giữ nguyên + dòng mới của ngày ds
        history.write_text("\n".join(kept + [line]) + "\n")
        log.info("history.jsonl: %d dòng", len(kept) + 1)
        return line

    @task
    def report_naive(meta: dict, split_info: dict, ds: str = None) -> None:
        # Cách "tự nhiên" nhưng SAI: mở file chế độ append, thêm dòng.
        # Chạy lại ngày ds → thêm một dòng trùng.
        line = json.dumps({"ds": ds, "rows": meta["rows"], **split_info}, sort_keys=True)
        with open(STAGING / "history_naive.jsonl", "a") as f:
            f.write(line + "\n")

    ingested = ingest()
    split_info = split(ingested)
    report(ingested, split_info)
    report_naive(ingested, split_info)


lesson04_idempotent()
