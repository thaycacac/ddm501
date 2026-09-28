"""
BÀI 08 — Thấy LocalExecutor chạy song song.

  start ─┬─► work_1 ─┐
         ├─► ...     ├─► summary
         └─► work_6 ─┘

Mỗi work_i ngủ `seconds` giây rồi báo hostname + pid của tiến trình chạy nó.
  SequentialExecutor (bài 01–07): 6 × 15s ≈ 90s
  LocalExecutor, parallelism 32:  ≈ 15s (+ vài giây khởi động mỗi task)
  LocalExecutor, parallelism 2:   ≈ 45s (từng cặp)
"""
import os
import socket
import time
from datetime import datetime

from airflow.decorators import dag, task
from airflow.models.param import Param

N_WORKERS = 6


@dag(
    dag_id="lesson08_parallel",
    schedule=None,
    start_date=datetime(2026, 9, 1),
    catchup=False,
    params={"seconds": Param(15, type="integer", minimum=1, maximum=120)},
    tags=["airflow-course", "lesson-08"],
)
def lesson08_parallel():

    @task
    def start() -> float:
        return time.time()

    @task
    def work(i: int, params: dict = None) -> dict:
        began = time.time()
        time.sleep(int(params["seconds"]))
        # hostname = container đang chạy task (trùng hostname của container scheduler);
        # pid khác nhau = mỗi task là một tiến trình con riêng của LocalExecutor
        return {"i": i, "host": socket.gethostname(), "pid": os.getpid(), "began": began, "ended": time.time()}

    @task
    def summary(results: list, t0: float) -> None:
        for r in sorted(results, key=lambda r: r["began"]):
            print(f"work_{r['i']}  host={r['host']}  pid={r['pid']}  "
                  f"bắt đầu +{r['began'] - t0:5.1f}s  xong +{r['ended'] - t0:5.1f}s")
        busy = sum(r["ended"] - r["began"] for r in results)
        wall = max(r["ended"] for r in results) - t0
        print(f"Tổng thời gian ngủ = {busy:.0f}s | thời gian thực từ start = {wall:.0f}s "
              f"→ song song ≈ {busy / wall:.1f} task cùng lúc")

    t0 = start()
    # Danh sách XComArg truyền vào summary → Airflow tự lấy kết quả của từng work_i (fan-in, bài 03)
    results = [work.override(task_id=f"work_{i}")(i) for i in range(1, N_WORKERS + 1)]
    t0 >> results
    summary(results, t0)


lesson08_parallel()
