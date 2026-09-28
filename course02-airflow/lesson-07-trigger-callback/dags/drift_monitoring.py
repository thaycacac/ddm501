"""
BÀI 07 — Bản gần giống hệt tutorial07/airflow_dags/drift_monitoring.py.

  run_drift_analysis ─► decide ─┬─► alert_drift (Telegram) ─► trigger_model_retrain ══► lesson07_model_retrain
                                └─► no_drift

Khác bài 06: alert_drift gửi Telegram thật, trigger_model_retrain là TriggerDagRunOperator thật.
Khác tutorial07: kết quả Evidently vẫn GIẢ LẬP bằng param (Evidently thật ghép ở Capstone T07);
thêm param fail_analysis để xem retry + on_failure_callback.
"""
from typing import Any, Dict

from airflow import DAG
from airflow.decorators import task
from airflow.models.param import Param
from airflow.operators.empty import EmptyOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator

from utils.common import DEFAULT_ARGS, START_DATE
from utils.telegram_alert import escape, send_telegram_message

FEATURES = ["fixed_acidity", "volatile_acidity", "citric_acid", "residual_sugar", "chlorides",
            "free_sulfur_dioxide", "total_sulfur_dioxide", "density", "pH", "sulphates", "alcohol"]


with DAG(
    dag_id="lesson07_drift_monitoring",
    schedule=None,                 # tutorial07: "@hourly"
    start_date=START_DATE,
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,     # retries=1 + on_failure_callback cho MỌI task bên dưới
    params={
        "threshold": Param(0.1, type="number", minimum=0, maximum=1),
        "window_size": Param(100, type="integer", minimum=1),
        "simulated_share": Param(0.3, type="number", minimum=0, maximum=1,
                                 description="GIẢ LẬP: tỷ lệ feature drift Evidently trả về"),
        "simulate_not_ready": Param(False, type="boolean",
                                    description="GIẢ LẬP: Evidently trả 400 → skipped, run vẫn xanh"),
        "fail_analysis": Param(False, type="boolean",
                               description="GIẢ LẬP: Evidently sập (500) → retry 1 lần → fail → callback Telegram"),
    },
    tags=["airflow-course", "lesson-07"],
) as dag:

    @task
    def run_drift_analysis(params: Dict[str, Any] = None, ti=None) -> Dict[str, Any]:
        threshold = float(params["threshold"])
        if params["fail_analysis"]:
            # tutorial07: response.raise_for_status() khi Evidently trả 5xx / mất kết nối.
            # Lỗi TẠM THỜI → raise exception thường → Airflow retry (retries=1). Hết retry vẫn lỗi
            # → task failed → on_failure_callback gửi Telegram.
            raise RuntimeError(f"Evidently HTTP 500 (giả lập), lần thử {ti.try_number}")
        if params["simulate_not_ready"]:
            return {"status": "skipped", "detail": "Mới có 12 mẫu, cần >= 100", "threshold": threshold}

        share = float(params["simulated_share"])
        drifted = round(share * len(FEATURES))
        return {
            "status": "success",
            "drifted_share": share,
            "drifted_count": drifted,
            "total_features": len(FEATURES),
            "drifted_features": FEATURES[:drifted],
            "threshold": threshold,
            "is_drift": share > threshold,
        }

    @task.branch
    def decide(result: Dict[str, Any]) -> str:
        if result.get("status") == "skipped":
            return "no_drift"
        return "alert_drift" if result.get("is_drift") else "no_drift"

    @task
    def alert_drift(result: Dict[str, Any]) -> None:
        # Nội dung tin nhắn = tutorial07 dòng 81–90 (bỏ dòng Samples/Report vì đang giả lập)
        features = ", ".join(result.get("drifted_features") or []) or "-"
        ok = send_telegram_message("\n".join([
            "<b>[DRIFT] Data drift detected</b>",
            f"Drifted features: {result['drifted_count']}/{result['total_features']} "
            f"(share {result['drifted_share']:.0%}, threshold {result['threshold']:.0%})",
            f"Features: <code>{escape(features)}</code>",
            "Action: triggering DAG <code>lesson07_model_retrain</code>",
        ]))
        # Gửi hỏng KHÔNG làm task fail (best effort) — chỉ in ra để bạn thấy trong log
        print(f"Telegram sent = {ok}")

    # TriggerDagRunOperator: tạo một DAG RUN MỚI cho DAG khác (giống bấm Trigger trên UI).
    #  - trigger_dag_id: DAG đích. Nếu DAG đích đang PAUSED, run vẫn được tạo nhưng nằm "queued" mãi.
    #  - conf: truyền sang DAG đích (thành dag_run.conf bên đó, ghi đè params cùng tên). Là field
    #    TEMPLATE → {{ run_id }} được thay bằng run_id của run hiện tại. Giá trị render ra là STRING.
    #  - wait_for_completion=False: tạo run xong là task này success, không chờ train xong.
    #    True → task chờ (poke mỗi poke_interval giây) tới khi run đích xong; đích fail → task này fail.
    trigger_retrain = TriggerDagRunOperator(
        task_id="trigger_model_retrain",
        trigger_dag_id="lesson07_model_retrain",
        conf={"reason": "drift_monitoring run {{ run_id }}"},
        wait_for_completion=False,
    )

    no_drift = EmptyOperator(task_id="no_drift")

    analysis = run_drift_analysis()
    branch = decide(analysis)
    branch >> no_drift
    branch >> alert_drift(analysis) >> trigger_retrain
