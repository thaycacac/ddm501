"""
BÀI 06 — Khung của tutorial07/airflow_dags/drift_monitoring.py: Params + rẽ nhánh.

  run_drift_analysis ─► decide ─┬─► alert_drift ─► trigger_model_retrain ─┐
                                └─► no_drift ─────────────────────────────┴─► record_decision

Kết quả Evidently được GIẢ LẬP bằng param `simulated_share` / `simulate_not_ready` để tập trung
vào Airflow. Bài 07 thay trigger_model_retrain bằng TriggerDagRunOperator thật và gửi Telegram.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from airflow.decorators import dag, task
from airflow.models.param import Param
from airflow.operators.empty import EmptyOperator
from airflow.utils.trigger_rule import TriggerRule

log = logging.getLogger(__name__)

DECISIONS = Path(__file__).resolve().parents[1] / "data" / "decisions.jsonl"
TOTAL_FEATURES = 11


@dag(
    dag_id="lesson06_drift_decision",
    schedule=None,              # tutorial07: "@hourly" — chạy theo lịch thì mọi param lấy giá trị mặc định
    start_date=datetime(2026, 9, 1),
    catchup=False,
    # Tối đa 1 run cùng lúc (= tutorial07). Phân tích drift chồng lên nhau chỉ tốn tài nguyên và
    # có thể trigger train lại 2 lần.
    max_active_runs=1,
    # Param = tham số của DAG: có giá trị mặc định, kiểu, ràng buộc.
    #  - Trigger trên UI → Airflow sinh FORM từ đây (ô số, checkbox...).
    #  - Trigger kèm conf (UI/CLI/API) → conf GHI ĐÈ giá trị mặc định, rồi bị KIỂM TRA theo
    #    type/minimum/maximum/enum. Sai → không tạo được run.
    params={
        "threshold": Param(0.1, type="number", minimum=0, maximum=1,
                           description="Tỷ lệ feature drift vượt mức này thì coi là drift (= tutorial07)"),
        "window_size": Param(100, type="integer", minimum=1,
                             description="Số mẫu production gần nhất đem phân tích (= tutorial07)"),
        "simulated_share": Param(0.3, type="number", minimum=0, maximum=1,
                                 description="GIẢ LẬP: tỷ lệ feature drift mà Evidently trả về"),
        "simulate_not_ready": Param(False, type="boolean",
                                    description="GIẢ LẬP: Evidently trả 400 (chưa có reference / chưa đủ mẫu)"),
    },
    tags=["airflow-course", "lesson-06"],
)
def lesson06_drift_decision():

    @task
    def run_drift_analysis(params: dict = None, dag_run=None) -> dict:
        # `params` = giá trị cuối cùng (mặc định đã bị conf ghi đè). `dag_run.conf` = đúng cái
        # người trigger gửi lên (rỗng khi chạy theo lịch). Airflow tự truyền vì tên tham số.
        log.info("params       = %s", dict(params))
        log.info("dag_run.conf = %s", dag_run.conf)

        threshold = float(params["threshold"])
        if params["simulate_not_ready"]:
            # tutorial07: HTTP 400 → trả status "skipped" chứ KHÔNG raise → run không đỏ
            # (chưa có dữ liệu là trạng thái bình thường lúc mới dựng hệ thống, không phải lỗi).
            return {"status": "skipped", "detail": "Mới có 12 mẫu, cần >= 100", "threshold": threshold}

        share = float(params["simulated_share"])
        return {
            "status": "success",
            "drifted_share": share,
            "drifted_count": round(share * TOTAL_FEATURES),
            "total_features": TOTAL_FEATURES,
            "window_size": int(params["window_size"]),
            "threshold": threshold,
            "is_drift": share > threshold,
        }

    # @task.branch: hàm trả về task_id (hoặc list task_id) của nhánh ĐƯỢC CHẠY.
    # Mọi task con trực tiếp KHÔNG được chọn → skipped (hồng), và skipped lan xuống dưới chúng.
    # Trả None hoặc [] → skip toàn bộ nhánh con.
    @task.branch
    def decide(result: dict) -> str:
        if result["status"] == "skipped":
            return "no_drift"
        return "alert_drift" if result["is_drift"] else "no_drift"

    @task
    def alert_drift(result: dict) -> None:
        # Bài 07: gửi Telegram thật. Ở đây chỉ log nội dung tin nhắn.
        log.info("[DRIFT] %d/%d feature (share %.0f%%, threshold %.0f%%) → sẽ trigger model_retrain",
                 result["drifted_count"], result["total_features"],
                 result["drifted_share"] * 100, result["threshold"] * 100)

    # EmptyOperator: task không làm gì. Dùng làm điểm đích của nhánh (no_drift) hoặc chỗ giữ chỗ.
    trigger_retrain = EmptyOperator(task_id="trigger_model_retrain")   # bài 07: TriggerDagRunOperator
    no_drift = EmptyOperator(task_id="no_drift")

    # Task GỘP sau rẽ nhánh. Mặc định trigger_rule="all_success": cần MỌI upstream success.
    # Sau branch luôn có một nhánh skipped → all_success không thỏa → task này cũng bị skip.
    # none_failed_min_one_success: không upstream nào failed VÀ ít nhất một cái success → chạy.
    # (tutorial07 không có task gộp nên không gặp chuyện này; DAG thật thường có — ghi log, dọn dẹp.)
    @task(trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS)
    def record_decision(result: dict, ds: str = None, run_id: str = None) -> None:
        line = {"ds": ds, "run_id": run_id, **result}
        DECISIONS.parent.mkdir(parents=True, exist_ok=True)
        with DECISIONS.open("a") as f:
            f.write(json.dumps(line) + "\n")
        log.info("ghi quyết định: %s", line)

    analysis = run_drift_analysis()
    branch = decide(analysis)
    alert = alert_drift(analysis)
    branch >> [alert, no_drift]
    alert >> trigger_retrain
    [trigger_retrain, no_drift] >> record_decision(analysis)


lesson06_drift_decision()
