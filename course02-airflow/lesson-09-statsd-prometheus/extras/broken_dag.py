"""
BÀI 09 — DAG CỐ Ý LỖI IMPORT. Không nằm trong dags/ để khỏi làm hỏng stack.

  cp extras/broken_dag.py dags/     → sau ~30–60s: banner "Broken DAG", airflow_dag_import_errors = 1
  rm dags/broken_dag.py             → về 0
"""
from datetime import datetime

from airflow.decorators import dag, task
from thu_vien_khong_ton_tai import something  # noqa: F401  ← ModuleNotFoundError khi scheduler parse


@dag(dag_id="lesson09_broken", schedule=None, start_date=datetime(2026, 9, 1), catchup=False)
def lesson09_broken():
    @task
    def noop() -> None:
        pass

    noop()


lesson09_broken()
