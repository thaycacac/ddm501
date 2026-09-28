"""
BÀI 07 — Giống tutorial07/airflow_dags/service_health_check.py.

  check_airflow ──┐
  check_evidently ┴─► report ─► (có service down) Telegram 1 tin + fail run

Trong stack bài này chỉ có Airflow → check_evidently luôn DOWN (không phân giải được tên "evidently").
Đó là cố ý: để thấy report gửi ĐÚNG MỘT tin tổng hợp và run đỏ, mà callback chung không gửi tin thứ hai.
"""
from typing import Any, Dict, List

import requests
from airflow import DAG
from airflow.decorators import task
from airflow.exceptions import AirflowFailException

from utils.common import DEFAULT_ARGS, START_DATE
from utils.telegram_alert import escape, send_telegram_message

HTTP_TIMEOUT_SECONDS = 5

SERVICES = {
    "airflow": "http://localhost:8080/health",     # webserver của chính container này
    "evidently": "http://evidently:8001/health",   # tutorial07 có; bài này không có → down
}


with DAG(
    dag_id="lesson07_service_health_check",
    schedule=None,                 # tutorial07: "*/15 * * * *"
    start_date=START_DATE,
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["airflow-course", "lesson-07"],
) as dag:

    # retries=0 + KHÔNG raise: service down là DỮ LIỆU (healthy=False), không phải task lỗi.
    # Nếu raise, mỗi service down sẽ bắn 1 callback riêng → spam N tin.
    @task(retries=0)
    def check_service(name: str, url: str) -> Dict[str, Any]:
        try:
            response = requests.get(url, timeout=HTTP_TIMEOUT_SECONDS)
        except requests.RequestException as exc:
            return {"service": name, "url": url, "healthy": False, "detail": f"{type(exc).__name__}: {exc}"[:300]}

        detail = f"HTTP {response.status_code}"
        healthy = response.status_code == 200
        try:
            body = response.json()
        except ValueError:
            body = None
        # Service trả {"status": "healthy"|"unhealthy"} thì tin vào status (HTTP 200 chưa chắc khỏe).
        # /health của Airflow không có khóa "status" ở ngoài cùng → chỉ xét HTTP 200.
        if healthy and isinstance(body, dict) and "status" in body:
            healthy = body["status"] == "healthy"
            detail = f"HTTP {response.status_code}, status={body['status']}"
        return {"service": name, "url": url, "healthy": healthy, "detail": detail}

    # on_failure_callback=None: GHI ĐÈ default_args cho riêng task này. report tự gửi tin tổng hợp rồi
    # mới raise; nếu để callback chung thì Telegram nhận thêm tin "[AIRFLOW] Task failed" trùng ý.
    @task(retries=0, on_failure_callback=None)
    def report(results: List[Dict[str, Any]]) -> Dict[str, Any]:
        down = [r for r in results if not r["healthy"]]
        for r in results:
            print(f"{r['service']:<10} healthy={r['healthy']} ({r['detail']})")
        if not down:
            return {"healthy": True, "checked": len(results)}

        lines = [f"<b>[HEALTH CHECK] {len(down)}/{len(results)} service down</b>"]
        for r in down:
            lines.append(f"- <b>{escape(r['service'])}</b> ({escape(r['url'])}): {escape(r['detail'])}")
        send_telegram_message("\n".join(lines))
        # Raise để run ĐỎ trên UI (và sau này thành metric dag failed ở bài 09)
        raise AirflowFailException(f"Services down: {', '.join(r['service'] for r in down)}")

    # .override(task_id=...): dùng lại 1 hàm @task cho nhiều task, mỗi task một id riêng.
    # Vòng for chạy lúc PARSE DAG → số task cố định theo SERVICES (không phải lúc run).
    checks = [check_service.override(task_id=f"check_{name}")(name, url) for name, url in SERVICES.items()]
    report(checks)
