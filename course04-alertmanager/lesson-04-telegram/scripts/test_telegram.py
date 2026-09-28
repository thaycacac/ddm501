"""
Kiểm tra bot Telegram trước khi giao cho Alertmanager (= tutorial07/scripts/test_telegram.sh).

  python3 scripts/test_telegram.py              # ghi secrets/telegram_bot_token + gửi tin thử
  python3 scripts/test_telegram.py --chat-ids   # liệt kê chat mà bot đã thấy (tìm chat_id)

Đọc TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID từ alertmanager-course/.env. Chỉ dùng thư viện chuẩn.
"""
import argparse
import json
import os
import socket
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Optional

COURSE = Path(__file__).resolve().parents[2]
ENV_FILE = COURSE / ".env"
SECRET_FILE = COURSE / "secrets" / "telegram_bot_token"


def read_env(key: str) -> str:
    # Biến môi trường của shell được ưu tiên, sau đó mới tới file .env.
    if os.getenv(key):
        return os.environ[key].strip()
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            if line.startswith(f"{key}="):
                return line.split("=", 1)[1].strip().strip("'\"")
    return ""


def call(token: str, method: str, params: Optional[dict] = None) -> dict:
    # Bot API: https://api.telegram.org/bot<TOKEN>/<method>. Token nằm TRONG URL → không bao giờ
    # in URL ra log (tutorial07 cũng cẩn thận điều này trong telegram_alert.py).
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = urllib.parse.urlencode(params).encode() if params else None
    try:
        with urllib.request.urlopen(url, data=data, timeout=15) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        # Telegram trả JSON mô tả lỗi, ví dụ {"ok":false,"description":"Bad Request: chat not found"}.
        return json.loads(e.read() or b"{}")
    except urllib.error.URLError as e:
        # Chưa tới được Telegram (mạng, DNS, TLS). Chỉ in lý do, không in URL vì URL chứa token.
        # CERTIFICATE_VERIFY_FAILED: Python không tin chứng chỉ server đưa ra. Python cài từ
        # python.org dùng bộ CA RIÊNG, không dùng Keychain của macOS; có thể chỉ định bộ CA khác
        # bằng biến môi trường SSL_CERT_FILE.
        raise SystemExit(f"Không kết nối được Telegram: {e.reason}")


def list_chats(token: str) -> None:
    # getUpdates trả các tin gần đây bot nhận được. Bot phải ở trong group và có ai đó
    # nhắn gì đó trong group trước, thì chat mới xuất hiện ở đây.
    chats = {}
    for update in call(token, "getUpdates").get("result", []):
        for key in ("message", "edited_message", "channel_post", "my_chat_member"):
            chat = (update.get(key) or {}).get("chat")
            if chat:
                chats[chat["id"]] = (chat.get("type"), chat.get("title") or chat.get("username"))
    if not chats:
        print("  (chưa có update — thêm bot vào group, nhắn một tin trong group rồi chạy lại)")
    for chat_id, (kind, title) in chats.items():
        # Group thường: id âm. Supergroup: id bắt đầu bằng -100. Group được nâng cấp lên
        # supergroup thì id ĐỔI → lỗi "chat not found" với id cũ.
        print(f"  {chat_id}\t{kind}\t{title}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chat-ids", action="store_true")
    ap.add_argument("message", nargs="?")
    args = ap.parse_args()

    token = read_env("TELEGRAM_BOT_TOKEN")
    chat_id = read_env("TELEGRAM_CHAT_ID")
    if not token:
        raise SystemExit(f"TELEGRAM_BOT_TOKEN trống. Điền vào {ENV_FILE}")

    if args.chat_ids:
        list_chats(token)
        return
    if not chat_id:
        raise SystemExit(f"TELEGRAM_CHAT_ID trống. Điền vào {ENV_FILE} (xem --chat-ids)")

    # Alertmanager đọc token từ FILE (bot_token_file), không từ biến môi trường hay config.
    # Ghi file với quyền 600 (chỉ chủ sở hữu đọc được). Thư mục secrets/ nằm trong .gitignore.
    # Phải có file này TRƯỚC khi `docker compose up`, nếu không Docker tự tạo một THƯ MỤC cùng tên.
    SECRET_FILE.parent.mkdir(exist_ok=True)
    if not SECRET_FILE.exists() or SECRET_FILE.read_text() != token:
        SECRET_FILE.write_text(token)
        SECRET_FILE.chmod(0o600)
        print(f"Đã ghi {SECRET_FILE.relative_to(COURSE)}")

    text = args.message or (f"alertmanager-course: tin thử từ {socket.gethostname()} "
                            f"lúc {datetime.now():%Y-%m-%d %H:%M:%S}")
    resp = call(token, "sendMessage", {"chat_id": chat_id, "text": text})
    if resp.get("ok"):
        print(f"Đã gửi tới chat {chat_id} (message_id={resp['result']['message_id']})")
    else:
        raise SystemExit(f"Telegram báo lỗi: {resp.get('description', resp)}\n"
                         "Nếu 'chat not found' hoặc group đã lên supergroup: chạy --chat-ids")


if __name__ == "__main__":
    main()
