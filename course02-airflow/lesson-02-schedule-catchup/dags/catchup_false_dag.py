"""
BÀI 02 — Giống hệt catchup_true_dag.py, chỉ khác catchup=False.

Bật lên → Airflow chỉ tạo run cho ngày GẦN NHẤT đã kết thúc, bỏ qua các ngày
trước đó. Đây là cấu hình của tutorial04 (wdbc_pipeline, dòng 43).
"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from airflow.decorators import dag, task

log = logging.getLogger(__name__)

DAG_ID = "lesson02_catchup_false"
STAGING = Path(__file__).resolve().parents[1] / "data" / "staging"


@dag(
    dag_id=DAG_ID,
    description="@daily from 2026-09-20, catchup=False",
    schedule="@daily",
    start_date=datetime(2026, 9, 20),
    catchup=False,                     # ← khác biệt duy nhất
    max_active_runs=1,
    tags=["airflow-course", "lesson-02"],
)
def lesson02_catchup_false():

    @task
    def show_dates(
        ds: str = None,
        logical_date=None,
        data_interval_start=None,
        data_interval_end=None,
        run_id: str = None,
    ) -> None:
        log.info("run_id              = %s", run_id)
        log.info("ds                  = %s", ds)
        log.info("logical_date        = %s", logical_date)
        log.info("data_interval_start = %s", data_interval_start)
        log.info("data_interval_end   = %s", data_interval_end)
        log.info("chạy thật lúc (UTC) = %s", datetime.utcnow().isoformat(timespec="seconds"))

        out_dir = STAGING / DAG_ID
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{ds}.txt").write_text(
            f"ds={ds}\ninterval=[{data_interval_start}, {data_interval_end})\nrun_id={run_id}\n"
        )

    show_dates()


lesson02_catchup_false()
