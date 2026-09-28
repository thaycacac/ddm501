"""
BÀI 10 — tutorial07/airflow_dags/model_retrain.py chạy THẬT với MLflow (course01 bài 16) + API.

  train_model ─► quality_gate ─► promote_model ─► reload_api ─► notify_success
      │               │               │                │
   MLflow run      so ngưỡng       stage Production   POST api:8000/model/reload
   + version mới   (+ so với        + alias champion   (kiểm tra API đang phục vụ đúng version)
                    bản Production)

Giữ đúng ý tutorial07: version LUÔN được đăng ký; chỉ bước PROMOTE bị gate chặn.
Bổ sung: param require_better (challenger phải >= champion), kiểm tra version sau reload.
"""
from typing import Any, Dict

import requests
from airflow import DAG
from airflow.decorators import task
from airflow.exceptions import AirflowFailException, AirflowSkipException
from airflow.models.param import Param

from utils.common import API_URL, DEFAULT_ARGS, MLFLOW_PUBLIC_URL, RETRAIN_MIN_ACCURACY, START_DATE
from utils.telegram_alert import escape, send_telegram_message

RELOAD_TIMEOUT_SECONDS = 120


with DAG(
    dag_id="lesson10_model_retrain",
    schedule=None,
    start_date=START_DATE,
    catchup=False,
    max_active_runs=1,          # hai lần train cùng lúc sẽ tranh nhau promote
    default_args=DEFAULT_ARGS,
    params={
        "min_accuracy": Param(RETRAIN_MIN_ACCURACY, type="number", minimum=0, maximum=1.5,
                              description="Ngưỡng accuracy để promote (> 1 → chắc chắn fail)"),
        "reason": Param("manual", type="string"),
        "n_estimators": Param(100, type="integer", minimum=1, maximum=500),
        "max_depth": Param(10, type="integer", minimum=1, maximum=50),
        "require_better": Param(False, type="boolean",
                                description="Chỉ promote nếu accuracy >= bản Production hiện tại"),
    },
    tags=["airflow-course", "lesson-10", "mlflow"],
) as dag:

    @task
    def train_model(dag_run=None, params: Dict[str, Any] = None) -> Dict[str, Any]:
        # Import LÚC CHẠY: scheduler parse DAG vài chục giây một lần; import mlflow + sklearn ở đầu file
        # làm mỗi lần parse chậm, và MLflow sập thì DAG thành Broken DAG. (= tutorial07)
        from training import train_and_register

        reason = (dag_run.conf or {}).get("reason") or params["reason"]
        result = train_and_register(
            run_name=f"airflow_retrain_{dag_run.run_id}",
            params={"n_estimators": params["n_estimators"], "max_depth": params["max_depth"]},
            # Tag nối ngược MLflow run → Airflow run (lineage, course01 bài 10)
            tags={"trigger": "airflow", "reason": reason, "airflow_run_id": dag_run.run_id},
        )
        if not result["version"]:
            raise AirflowFailException("Model đã log nhưng không thấy version trong registry")
        result["reason"] = reason
        print(f"Đăng ký {result['model_name']} v{result['version']} metrics={result['metrics']}")
        return result

    @task
    def quality_gate(result: Dict[str, Any], params: Dict[str, Any] = None) -> Dict[str, Any]:
        from training import get_production

        accuracy = result["metrics"]["accuracy"]
        min_accuracy = float(params["min_accuracy"])
        production = get_production()
        result["previous_production"] = production
        print(f"challenger v{result['version']} accuracy={accuracy:.4f} | min={min_accuracy} | "
              f"champion={production}")

        if accuracy < min_accuracy:
            # LỖI: model mới dưới chuẩn tối thiểu → đỏ + Telegram (callback). Không retry: chạy lại vẫn vậy.
            raise AirflowFailException(
                f"Quality gate failed: accuracy {accuracy:.4f} < min_accuracy {min_accuracy:.4f} "
                f"(version {result['version']} stays unpromoted)"
            )
        if params["require_better"] and production and production["accuracy"] is not None \
                and accuracy < production["accuracy"]:
            # KHÔNG phải lỗi: model mới đạt chuẩn nhưng kém bản đang chạy → giữ bản cũ.
            # AirflowSkipException → task skipped, các task sau (all_success) cũng skipped, run vẫn XANH.
            raise AirflowSkipException(
                f"v{result['version']} ({accuracy:.4f}) kém champion v{production['version']} "
                f"({production['accuracy']:.4f}) → không promote"
            )
        return result

    @task
    def promote_model(result: Dict[str, Any]) -> Dict[str, Any]:
        from training import promote_to_production

        promote_to_production(result["version"])
        print(f"Promote {result['model_name']} v{result['version']} → stage Production + alias champion")
        return result

    @task
    def reload_api(result: Dict[str, Any]) -> Dict[str, Any]:
        response = requests.post(f"{API_URL}/model/reload", timeout=RELOAD_TIMEOUT_SECONDS)
        response.raise_for_status()
        body = response.json()
        served = str(body.get("model_version"))
        print(f"API reload: {body}")
        # tutorial07 chỉ ghi lại version API trả về. Ở đây KIỂM TRA: registry đã promote v5 mà API vẫn
        # phục vụ v4 là trạng thái sai → fail (retry 1 lần) để người trực biết.
        if served != str(result["version"]):
            raise RuntimeError(f"API đang phục vụ v{served}, kỳ vọng v{result['version']}")
        result["api_model_version"] = served
        return result

    @task
    def notify_success(result: Dict[str, Any]) -> None:
        m = result["metrics"]
        prev = result.get("previous_production") or {}
        send_telegram_message("\n".join([
            "<b>[RETRAIN] Model promoted to Production</b>",
            f"Model: <code>{escape(result['model_name'])}</code> v{escape(result['version'])} "
            f"(API serving v{escape(result.get('api_model_version', '?'))})",
            f"Accuracy: {m['accuracy']:.4f} | F1: {m['f1_score']:.4f}",
            f"Precision: {m['precision']:.4f} | Recall: {m['recall']:.4f}",
            f"Previous: v{escape(prev.get('version', '-'))}",
            f"Reason: {escape(result.get('reason', '-'))}",
            f"MLflow run: {escape(MLFLOW_PUBLIC_URL)}/#/experiments/{escape(result['experiment_id'])}"
            f"/runs/{escape(result['run_id'])}",
        ]))

    notify_success(reload_api(promote_model(quality_gate(train_model()))))
