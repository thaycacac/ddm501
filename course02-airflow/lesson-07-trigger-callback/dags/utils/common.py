"""
BÀI 07 — Cấu hình dùng chung cho các DAG, giống tutorial07/airflow_dags/utils/common.py.

utils/ nằm TRONG thư mục dags/ (Airflow tự thêm dags/ vào sys.path → `from utils.common import ...`
chạy được), còn .airflowignore có dòng `utils/` để scheduler không phí công quét nó tìm DAG.
"""
import os
from datetime import datetime, timedelta

from utils.telegram_alert import task_failure_alert

RETRAIN_MIN_ACCURACY = float(os.getenv("RETRAIN_MIN_ACCURACY", "0.8"))

START_DATE = datetime(2026, 9, 1)

# default_args áp cho MỌI task của DAG dùng nó; task nào cần khác thì ghi đè trong @task(...)
DEFAULT_ARGS = {
    "owner": "mlops",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(seconds=10),     # tutorial07: 1 phút; rút ngắn cho bài học
    # Callback MỨC TASK: task fail hẳn (hết retry) → gọi task_failure_alert(context).
    # Lần fail còn retry KHÔNG gọi hàm này (đó là việc của on_retry_callback).
    "on_failure_callback": task_failure_alert,
}
