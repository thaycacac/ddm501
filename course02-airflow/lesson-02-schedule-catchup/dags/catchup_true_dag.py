"""
BÀI 02 — DAG chạy mỗi ngày, catchup=True.

Bật lên → Airflow tạo run cho MỌI ngày từ start_date tới ngày gần nhất đã
kết thúc. Mỗi run ghi một file data/staging/lesson02_catchup_true/<ds>.txt.
"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from airflow.decorators import dag, task

log = logging.getLogger(__name__)

DAG_ID = "lesson02_catchup_true"
STAGING = Path(__file__).resolve().parents[1] / "data" / "staging"


@dag(
    dag_id=DAG_ID,
    description="@daily from 2026-09-20, catchup=True",
    schedule="@daily",                 # mỗi khoảng = 1 ngày UTC, bắt đầu 00:00
    start_date=datetime(2026, 9, 20),  # cố định; datetime không múi giờ = UTC
    catchup=True,                      # chạy bù mọi ngày đã qua
    max_active_runs=1,                 # chạy bù lần lượt, không chồng nhau
    tags=["airflow-course", "lesson-02"],
)
def lesson02_catchup_true():

    @task
    def show_dates(
        # Airflow thấy tham số trùng tên biến context → tự truyền giá trị vào.
        # Mặc định None để file vẫn import được khi không có Airflow chạy nó.
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
        # So sánh với giờ THẬT lúc task chạy: ds luôn là ngày đã qua
        log.info("chạy thật lúc (UTC) = %s", datetime.utcnow().isoformat(timespec="seconds"))

        out_dir = STAGING / DAG_ID
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{ds}.txt").write_text(
            f"ds={ds}\ninterval=[{data_interval_start}, {data_interval_end})\nrun_id={run_id}\n"
        )

    show_dates()


lesson02_catchup_true()
