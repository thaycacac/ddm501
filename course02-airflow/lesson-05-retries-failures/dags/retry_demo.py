"""
BÀI 05 — Retry + exponential backoff.

Task flaky_fetch giả lập nguồn dữ liệu chập chờn:
  lần 1: lỗi   → up_for_retry, chờ ~10–20s
  lần 2: lỗi   → up_for_retry, chờ ~20–40s (backoff: lần sau chờ lâu hơn)
  lần 3: thành công
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from airflow.decorators import dag, task

log = logging.getLogger(__name__)

SUCCEED_ON_ATTEMPT = 3   # lỗi ở các lần trước lần này


@dag(
    dag_id="lesson05_retry_demo",
    schedule=None,
    start_date=datetime(2026, 9, 1),
    catchup=False,
    # default_args: giá trị mặc định cho MỌI task trong DAG (= tutorial04 dòng 45–49)
    default_args={
        "retries": 3,                           # thử lại tối đa 3 lần
        "retry_delay": timedelta(seconds=10),   # mốc chờ cơ bản
        "retry_exponential_backoff": True,      # lần chờ sau ≈ gấp đôi lần trước
    },
    tags=["airflow-course", "lesson-05"],
)
def lesson05_retry_demo():

    @task
    def flaky_fetch(ti=None) -> dict:
        # ti = TaskInstance hiện tại (Airflow tự truyền vì tham số tên "ti").
        # ti.try_number = lần chạy thứ mấy của task này trong run này: 1, 2, 3...
        attempt = ti.try_number
        log.info("attempt %d / tối đa %d", attempt, 1 + ti.max_tries)
        if attempt < SUCCEED_ON_ATTEMPT:
            # Exception THƯỜNG → Airflow hiểu là lỗi tạm thời → được retry
            raise ConnectionError(f"simulated network blip on attempt {attempt}")
        log.info("source reachable on attempt %d", attempt)
        return {"attempts_needed": attempt}

    flaky_fetch()


lesson05_retry_demo()
