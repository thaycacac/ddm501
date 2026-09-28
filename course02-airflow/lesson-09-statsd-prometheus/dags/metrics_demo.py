"""
BÀI 09 — DAG sinh metric đều đặn để có cái mà nhìn trên Prometheus.

  extract ─► transform ─► load

  - Chạy theo lịch mỗi 2 phút (DAG không pause sẵn) → luôn có run success
  - Trigger với {"fail": true}      → load fail  → dagrun.duration.failed + ti.finish...failed
  - Trigger với {"seconds": 90}     → transform quá execution_timeout 60s → bị kill → failed
"""
import time
from datetime import datetime, timedelta

from airflow.decorators import dag, task
from airflow.exceptions import AirflowFailException
from airflow.models.param import Param


@dag(
    dag_id="lesson09_metrics_demo",
    schedule="*/2 * * * *",
    start_date=datetime(2026, 9, 1),
    catchup=False,
    max_active_runs=3,
    default_args={"retries": 0},
    params={
        "fail": Param(False, type="boolean", description="load raise lỗi → run failed"),
        "seconds": Param(3, type="integer", minimum=1, maximum=300,
                         description="transform ngủ bao lâu (> 60 → quá execution_timeout)"),
    },
    tags=["airflow-course", "lesson-09"],
)
def lesson09_metrics_demo():

    @task
    def extract() -> int:
        time.sleep(1)
        return 100

    # execution_timeout: task chạy quá thời gian này → Airflow kill, raise AirflowTaskTimeout → failed
    # (retry nếu còn lượt). Đây là cách chặn task treo — StatsD không đo được task đang chạy.
    @task(execution_timeout=timedelta(seconds=60))
    def transform(rows: int, params: dict = None) -> int:
        time.sleep(int(params["seconds"]))
        return rows * 2

    @task
    def load(rows: int, params: dict = None) -> None:
        if params["fail"]:
            raise AirflowFailException("Giả lập lỗi ghi kho dữ liệu")
        print(f"Đã ghi {rows} dòng")

    load(transform(extract()))


lesson09_metrics_demo()
