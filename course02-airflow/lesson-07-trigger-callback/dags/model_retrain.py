"""
BÀI 07 — Khung của tutorial07/airflow_dags/model_retrain.py (DAG ĐÍCH của TriggerDagRunOperator).

  train_model ─► quality_gate ─► promote_model ─► reload_api ─► notify_success (Telegram)

Train / MLflow / API đều GIẢ LẬP (bài 10 làm thật với MLflow course01):
  - accuracy lấy từ param simulated_accuracy
  - "registry" là file data/registry.json: mỗi lần train thêm 1 version, promote thì đổi production
Giữ nguyên ý của tutorial07: version LUÔN được đăng ký, chỉ bước PROMOTE bị quality gate chặn.
"""
import json
from pathlib import Path
from typing import Any, Dict

from airflow import DAG
from airflow.decorators import task
from airflow.exceptions import AirflowFailException
from airflow.models.param import Param

from utils.common import DEFAULT_ARGS, RETRAIN_MIN_ACCURACY, START_DATE
from utils.telegram_alert import escape, send_telegram_message

REGISTRY = Path(__file__).resolve().parents[1] / "data" / "registry.json"


def _load_registry() -> Dict[str, Any]:
    if REGISTRY.exists():
        return json.loads(REGISTRY.read_text())
    return {"versions": [], "production": None}


def _save_registry(reg: Dict[str, Any]) -> None:
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY.write_text(json.dumps(reg, indent=2))


with DAG(
    dag_id="lesson07_model_retrain",
    schedule=None,                 # chỉ chạy khi được trigger (tay hoặc từ drift_monitoring)
    start_date=START_DATE,
    catchup=False,
    # drift_monitoring trigger dồn dập → các run xếp hàng, không train chồng lên nhau
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    params={
        # maximum=1.5 để cố ý đặt > 1 → quality gate chắc chắn fail (mẹo của tutorial07)
        "min_accuracy": Param(RETRAIN_MIN_ACCURACY, type="number", minimum=0, maximum=1.5,
                              description="Ngưỡng accuracy để được promote"),
        "reason": Param("manual", type="string", description="Lý do train lại"),
        "simulated_accuracy": Param(0.85, type="number", minimum=0, maximum=1,
                                    description="GIẢ LẬP: accuracy của model mới"),
        "flaky_train": Param(False, type="boolean",
                             description="GIẢ LẬP: lần thử 1 lỗi tạm thời, lần 2 thành công (retry cứu)"),
    },
    tags=["airflow-course", "lesson-07"],
) as dag:

    @task
    def train_model(dag_run=None, params: Dict[str, Any] = None, ti=None) -> Dict[str, Any]:
        # conf từ drift_monitoring = {"reason": "drift_monitoring run ..."} đã GHI ĐÈ params["reason"].
        # tutorial07 đọc cả dag_run.conf lẫn params cho chắc; hai cách cho cùng kết quả.
        reason = (dag_run.conf or {}).get("reason") or params["reason"]
        print(f"dag_run.run_type = {dag_run.run_type}  (manual: bấm tay / TriggerDagRunOperator)")
        print(f"dag_run.conf     = {dag_run.conf}")
        print(f"reason           = {reason}")

        if params["flaky_train"] and ti.try_number == 1:
            # Lỗi tạm thời → retry sau 10s → lần 2 thành công. on_failure_callback KHÔNG được gọi.
            raise RuntimeError("MLflow tạm thời không phản hồi (giả lập)")

        reg = _load_registry()
        version = len(reg["versions"]) + 1
        metrics = {"accuracy": float(params["simulated_accuracy"])}
        reg["versions"].append({"version": version, "metrics": metrics, "reason": reason,
                                "airflow_run_id": dag_run.run_id})
        _save_registry(reg)
        print(f"Đã đăng ký v{version} metrics={metrics}")
        return {"model_name": "wine_quality_model", "version": version, "metrics": metrics, "reason": reason}

    @task
    def quality_gate(result: Dict[str, Any], params: Dict[str, Any] = None) -> Dict[str, Any]:
        accuracy = result["metrics"]["accuracy"]
        min_accuracy = float(params["min_accuracy"])
        if accuracy < min_accuracy:
            # AirflowFailException: fail NGAY, bỏ qua retry (chạy lại metric cũng không đổi)
            # → vẫn gọi on_failure_callback → Telegram "[AIRFLOW] Task failed".
            raise AirflowFailException(
                f"Quality gate failed: accuracy {accuracy:.4f} < min_accuracy {min_accuracy:.4f} "
                f"(version {result['version']} stays unpromoted)"
            )
        return result

    @task
    def promote_model(result: Dict[str, Any]) -> Dict[str, Any]:
        reg = _load_registry()
        reg["production"] = result["version"]
        _save_registry(reg)
        print(f"Promote {result['model_name']} v{result['version']} lên Production")
        return result

    @task
    def reload_api(result: Dict[str, Any]) -> Dict[str, Any]:
        # tutorial07: POST {API_URL}/model/reload rồi đọc model_version API đang phục vụ
        result["api_model_version"] = str(result["version"])
        print(f"(giả lập) API reload → đang phục vụ v{result['api_model_version']}")
        return result

    @task
    def notify_success(result: Dict[str, Any]) -> None:
        m = result["metrics"]
        send_telegram_message("\n".join([
            "<b>[RETRAIN] Model promoted to Production</b>",
            f"Model: <code>{escape(result['model_name'])}</code> v{escape(result['version'])} "
            f"(API serving v{escape(result.get('api_model_version', '?'))})",
            f"Accuracy: {m['accuracy']:.4f}",
            f"Reason: {escape(result.get('reason', '-'))}",
        ]))

    notify_success(reload_api(promote_model(quality_gate(train_model()))))
