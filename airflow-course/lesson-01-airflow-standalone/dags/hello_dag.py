"""
BÀI 01 — DAG đầu tiên: 2 task chạy nối tiếp.

  say_hello  ──►  write_file

Scheduler import file này định kỳ. Mọi code ở cấp module (ngoài hàm task) chạy
MỖI LẦN parse → chỉ đặt định nghĩa DAG ở đây, việc nặng để trong task.
"""
from __future__ import annotations

import logging
import socket
from datetime import datetime
from pathlib import Path

from airflow.decorators import dag, task

log = logging.getLogger(__name__)

# /opt/airflow/dags/hello_dag.py → parents[1] = /opt/airflow
# → /opt/airflow/data là thư mục ./data trên máy bạn (bind mount)
STAGING = Path(__file__).resolve().parents[1] / "data" / "staging"


@dag(
    dag_id="hello_airflow",        # tên hiện trên UI, dùng trong mọi lệnh CLI
    schedule=None,                 # không tự chạy theo lịch — chỉ chạy khi bạn trigger
    start_date=datetime(2026, 9, 1),
    catchup=False,                 # bài 02 sẽ giải thích schedule / start_date / catchup
    tags=["airflow-course", "lesson-01"],
)
def hello_airflow():

    @task
    def say_hello() -> None:
        # log.info → hiện trong tab Logs của task instance trên UI (và file trong logs/)
        log.info("Xin chào từ Airflow! Task này chạy trong container %s", socket.gethostname())

    @task
    def write_file() -> None:
        STAGING.mkdir(parents=True, exist_ok=True)
        out = STAGING / "hello.txt"
        out.write_text(f"written by hello_airflow at {datetime.now().isoformat()}\n")
        log.info("đã ghi %s", out)

    # >> đặt thứ tự: say_hello xong (thành công) mới tới write_file
    say_hello() >> write_file()


# Gọi hàm để tạo đối tượng DAG. Thiếu dòng này → Airflow không thấy DAG nào.
hello_airflow()
