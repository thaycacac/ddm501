"""
BÀI 05 — Quarantine + ngưỡng + AirflowFailException (= task validate của tutorial04).

  ingest ─► validate ─► report

- Dòng xấu → rejected.parquet (cách ly), dòng sạch → clean.parquet.
- Tỉ lệ xấu > 5% → AirflowFailException: FAIL NGAY, không retry.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from airflow.decorators import dag, task
from airflow.exceptions import AirflowFailException

log = logging.getLogger(__name__)

PROJECT = Path(__file__).resolve().parents[1]
RAW = PROJECT / "data" / "raw" / "readings.csv"
STAGING = PROJECT / "data" / "staging"

HUMIDITY_MIN, HUMIDITY_MAX = 0.0, 100.0   # độ ẩm hợp lệ trong khoảng 0–100%
LABELS = {"OK", "WET"}                    # giá trị status hợp lệ
MAX_BAD_FRACTION = 0.05                   # > 5% dòng xấu → nguồn không dùng được


def run_dir(ds: str) -> Path:
    d = STAGING / ds
    d.mkdir(parents=True, exist_ok=True)
    return d


@dag(
    dag_id="lesson05_quarantine",
    schedule=None,                        # trigger tay để dễ quan sát
    start_date=datetime(2026, 9, 1),
    catchup=False,
    default_args={                        # giống hệt tutorial04
        "retries": 3,
        "retry_delay": timedelta(seconds=10),
        "retry_exponential_backoff": True,
    },
    tags=["airflow-course", "lesson-05"],
)
def lesson05_quarantine():

    @task
    def ingest(ds: str = None) -> dict:
        if not RAW.exists():
            # Thiếu file nguồn: retry cũng không làm file tự xuất hiện → fail ngay
            raise AirflowFailException(f"source extract missing: {RAW}")
        frame = pd.read_csv(RAW)
        out = run_dir(ds) / "raw.parquet"
        frame.to_parquet(out, index=False)          # snapshot (bài 04)
        log.info("ingested %d rows", len(frame))
        return {"rows": len(frame), "path": str(out)}

    @task
    def validate(meta: dict, ds: str = None) -> dict:
        frame = pd.read_parquet(meta["path"])

        # Mỗi cột = một loại lỗi, mỗi dòng True/False (= tutorial04 dòng 77–84)
        problems = pd.DataFrame(index=frame.index)
        problems["null"] = frame["humidity"].isna()
        problems["out_of_range"] = ~frame["humidity"].between(HUMIDITY_MIN, HUMIDITY_MAX) & frame["humidity"].notna()
        problems["bad_label"] = ~frame["status"].isin(LABELS)
        problems["duplicate"] = frame.duplicated(subset="reading_id", keep="first")

        bad = problems.any(axis=1)                   # dòng có ít nhất 1 lỗi
        counts = {k: int(v) for k, v in problems.sum().items()}
        fraction = float(bad.mean())                 # tỉ lệ dòng xấu
        log.info("validation: %s  (%.1f%% rows rejected)", counts, fraction * 100)

        # Luôn ghi 3 file này, KỂ CẢ khi sắp fail → có bằng chứng để điều tra
        frame[bad].to_parquet(run_dir(ds) / "rejected.parquet", index=False)
        clean_path = run_dir(ds) / "clean.parquet"
        frame[~bad].to_parquet(clean_path, index=False)
        (run_dir(ds) / "validation_report.json").write_text(json.dumps(
            {"counts": counts, "bad_fraction": fraction, "clean_rows": int((~bad).sum())}, indent=2))

        if fraction > MAX_BAD_FRACTION:
            # Nguồn hỏng nặng: lần thử thứ 2, 3, 4 vẫn hỏng y như vậy
            # → AirflowFailException bỏ qua retry (= tutorial04 dòng 100–104)
            raise AirflowFailException(
                f"{fraction:.1%} of rows rejected, limit is {MAX_BAD_FRACTION:.0%}")
        return {"path": str(clean_path), "clean_rows": int((~bad).sum()), **counts}

    @task
    def report(validation: dict, ds: str = None) -> str:
        summary = {"ds": ds, **validation}
        summary.pop("path", None)
        (run_dir(ds) / "summary.json").write_text(json.dumps(summary, indent=2))
        log.info("summary: %s", summary)
        return json.dumps(summary, sort_keys=True)

    report(validate(ingest()))


lesson05_quarantine()
