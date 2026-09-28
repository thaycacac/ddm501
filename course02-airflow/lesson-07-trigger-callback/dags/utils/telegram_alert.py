"""
BÀI 07 — Util Telegram, giống tutorial07/airflow_dags/utils/telegram_alert.py.

Nguyên tắc: gửi Telegram là BEST EFFORT. Lỗi mạng / sai token chỉ log rồi trả False, KHÔNG raise,
để việc báo động không bao giờ làm hỏng DAG run.
"""
import html
import logging
import os
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"
TELEGRAM_TIMEOUT_SECONDS = float(os.getenv("TELEGRAM_TIMEOUT_SECONDS", "10"))
TELEGRAM_MAX_MESSAGE_LENGTH = 4096   # giới hạn của Bot API; dài hơn → 400 Bad Request


def escape(value: Any) -> str:
    # parse_mode=HTML: tên task/lỗi có "<" ">" "&" sẽ làm Telegram từ chối cả tin nhắn → phải escape
    return html.escape(str(value), quote=False)


def send_telegram_message(text: str, parse_mode: Optional[str] = "HTML") -> bool:
    # Đọc env MỖI LẦN gọi (không đọc lúc import) → đổi .env + recreate container là có hiệu lực
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        logger.warning("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID chưa cấu hình, bỏ qua tin nhắn Telegram")
        return False

    if len(text) > TELEGRAM_MAX_MESSAGE_LENGTH:
        text = text[: TELEGRAM_MAX_MESSAGE_LENGTH - 20] + "\n...(truncated)"

    payload: Dict[str, Any] = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
    if parse_mode:
        payload["parse_mode"] = parse_mode

    try:
        response = requests.post(TELEGRAM_API_URL.format(token=token), json=payload,
                                 timeout=TELEGRAM_TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        # Thông điệp exception chứa URL, mà URL chứa TOKEN → chỉ log tên loại lỗi, tránh lộ secret ra log
        logger.warning("Gửi Telegram thất bại: %s", type(exc).__name__)
        return False

    if not response.ok:
        # Body lỗi của Telegram không chứa token, log được (vd 400 "can't parse entities")
        logger.warning("Telegram API lỗi %s: %s", response.status_code, response.text[:300])
        return False

    logger.info("Đã gửi Telegram tới chat %s", chat_id)
    return True


def task_failure_alert(context: Dict[str, Any]) -> None:
    """Dùng làm on_failure_callback: Airflow gọi hàm này với `context` khi task FAIL HẲN (hết retry)."""
    # Callback không được raise: exception ở đây chỉ bị log, còn tin báo lỗi thì mất → bọc try toàn bộ
    try:
        ti = context.get("task_instance")
        dag_run = context.get("dag_run")
        logical_date = context.get("logical_date")
        exception = context.get("exception")      # exception làm task fail

        dag_id = ti.dag_id if ti else context.get("dag").dag_id
        task_id = ti.task_id if ti else "-"
        run_id = dag_run.run_id if dag_run else context.get("run_id", "-")
        try_number = getattr(ti, "try_number", "-")
        max_tries = getattr(ti, "max_tries", None)   # = retries
        log_url = getattr(ti, "log_url", None)       # dựng từ AIRFLOW__WEBSERVER__BASE_URL

        lines = [
            "<b>[AIRFLOW] Task failed</b>",
            f"DAG: <code>{escape(dag_id)}</code>",
            f"Task: <code>{escape(task_id)}</code>",
            f"Run ID: <code>{escape(run_id)}</code>",
            f"Logical date: {escape(logical_date.isoformat() if logical_date else '-')}",
            f"Try: {escape(try_number)}" + (f"/{escape(max_tries + 1)}" if max_tries is not None else ""),
        ]
        if exception is not None:
            lines.append(f"Error: <code>{escape(type(exception).__name__)}: {escape(str(exception)[:500])}</code>")
        if log_url:
            lines.append(f'<a href="{html.escape(log_url, quote=True)}">Xem log</a>')

        send_telegram_message("\n".join(lines))
    except Exception:  # noqa: BLE001
        logger.exception("Không dựng/gửi được tin báo lỗi Telegram")
