"""
Telegram notifications for Airflow DAGs.

Reads TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID from the environment and calls the
Bot API ``sendMessage``. Sending is best effort: a Telegram/network error is
logged and never raised, so alerting can never fail a DAG run.
"""

import html
import logging
import os
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"
TELEGRAM_TIMEOUT_SECONDS = float(os.getenv("TELEGRAM_TIMEOUT_SECONDS", "10"))
TELEGRAM_MAX_MESSAGE_LENGTH = 4096


def escape(value: Any) -> str:
    """Escape a value for Telegram ``parse_mode=HTML``."""
    return html.escape(str(value), quote=False)


def send_telegram_message(text: str, parse_mode: Optional[str] = "HTML") -> bool:
    """Send ``text`` to the configured chat. Returns True when Telegram accepted it."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        logger.warning("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not configured, skip Telegram alert")
        return False

    if len(text) > TELEGRAM_MAX_MESSAGE_LENGTH:
        text = text[: TELEGRAM_MAX_MESSAGE_LENGTH - 20] + "\n...(truncated)"

    payload: Dict[str, Any] = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode

    try:
        response = requests.post(
            TELEGRAM_API_URL.format(token=token),
            json=payload,
            timeout=TELEGRAM_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        # The exception message contains the request URL (and therefore the token): log only the type.
        logger.warning("Telegram request failed: %s", type(exc).__name__)
        return False

    if not response.ok:
        logger.warning("Telegram API error %s: %s", response.status_code, response.text[:300])
        return False

    logger.info("Telegram alert sent to chat %s", chat_id)
    return True


def task_failure_alert(context: Dict[str, Any]) -> None:
    """``on_failure_callback``: report the failed task to Telegram."""
    try:
        ti = context.get("task_instance")
        dag_run = context.get("dag_run")
        logical_date = context.get("logical_date")
        exception = context.get("exception")

        dag_id = ti.dag_id if ti else context.get("dag").dag_id
        task_id = ti.task_id if ti else "-"
        run_id = dag_run.run_id if dag_run else context.get("run_id", "-")
        try_number = getattr(ti, "try_number", "-")
        max_tries = getattr(ti, "max_tries", None)
        log_url = getattr(ti, "log_url", None)

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
    except Exception:  # noqa: BLE001 - a callback must never raise
        logger.exception("Failed to build/send Telegram failure alert")
