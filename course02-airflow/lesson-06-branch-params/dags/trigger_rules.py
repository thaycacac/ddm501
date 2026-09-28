"""
BÀI 06 — trigger_rule của task GỘP sau rẽ nhánh, so sánh 3 cách cạnh nhau.

              ┌─► path_a ─┐      ┌─► join_all_success                  (mặc định)
  pick_path ──┤           ├──────┼─► join_none_failed_min_one_success
              └─► path_b ─┘      └─► join_all_done

Param `pick` chọn nhánh: a | b | both | none. `path_b` có thể cố ý lỗi (param `fail_b`).
"""
from __future__ import annotations

from datetime import datetime

from airflow.decorators import dag, task
from airflow.models.param import Param
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator
from airflow.utils.trigger_rule import TriggerRule


@dag(
    dag_id="lesson06_trigger_rules",
    schedule=None,
    start_date=datetime(2026, 9, 1),
    catchup=False,
    params={
        # enum: chỉ nhận đúng các giá trị này; form UI hiện thành dropdown
        "pick": Param("a", type="string", enum=["a", "b", "both", "none"],
                      description="Nhánh được chọn"),
        "fail_b": Param(False, type="boolean", description="path_b cố ý lỗi"),
    },
    tags=["airflow-course", "lesson-06"],
)
def lesson06_trigger_rules():

    @task.branch
    def pick_path(params: dict = None):
        return {"a": "path_a", "b": "path_b", "both": ["path_a", "path_b"], "none": None}[params["pick"]]

    path_a = EmptyOperator(task_id="path_a")

    # Param cũng dùng được trong TEMPLATE Jinja của operator cổ điển: {{ params.x }}, {{ dag_run.conf }}
    path_b = BashOperator(
        task_id="path_b",
        bash_command=(
            'echo "pick={{ params.pick }} fail_b={{ params.fail_b }} conf={{ dag_run.conf }}"; '
            "{% if params.fail_b %}exit 1{% endif %}"
        ),
        retries=0,
    )

    joins = [
        # cần MỌI upstream success
        EmptyOperator(task_id="join_all_success", trigger_rule=TriggerRule.ALL_SUCCESS),
        # không upstream nào failed/upstream_failed VÀ ít nhất 1 success
        EmptyOperator(task_id="join_none_failed_min_one_success",
                      trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS),
        # chỉ cần mọi upstream đã XONG (success/failed/skipped đều được) — hay dùng cho dọn dẹp
        EmptyOperator(task_id="join_all_done", trigger_rule=TriggerRule.ALL_DONE),
    ]

    pick_path() >> [path_a, path_b] >> joins[0]
    [path_a, path_b] >> joins[1]
    [path_a, path_b] >> joins[2]


lesson06_trigger_rules()
