#!/usr/bin/env bash
# ============================================
# TELEGRAM ALERT TEST
# ============================================
# 1. Loads TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID from .env (or the current environment)
# 2. Syncs secrets/telegram_bot_token (used by Alertmanager bot_token_file)
# 3. Sends a test message to the configured chat
#
# Usage: ./scripts/test_telegram.sh ["custom message"]
#        ./scripts/test_telegram.sh --chat-ids   # list chat IDs seen by the bot (getUpdates)

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"
SECRET_FILE="${ROOT_DIR}/secrets/telegram_bot_token"

read_env() {
  local key="$1"
  [ -f "${ENV_FILE}" ] || return 0
  grep -E "^${key}=" "${ENV_FILE}" | tail -n 1 | cut -d= -f2- | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//"
}

TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-$(read_env TELEGRAM_BOT_TOKEN)}"
TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-$(read_env TELEGRAM_CHAT_ID)}"

if [ -z "${TELEGRAM_BOT_TOKEN}" ]; then
  echo "❌ TELEGRAM_BOT_TOKEN is empty. Set it in ${ENV_FILE}" >&2
  exit 1
fi

API="https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}"

if [ "${1:-}" = "--chat-ids" ]; then
  echo "Chats seen by the bot (send a message in the group first):"
  curl -sS --max-time 15 "${API}/getUpdates" | python3 -c '
import json, sys
data = json.load(sys.stdin)
chats = {}
for update in data.get("result", []):
    for key in ("message", "edited_message", "channel_post", "my_chat_member"):
        chat = (update.get(key) or {}).get("chat")
        if chat:
            chats[chat["id"]] = (chat.get("type"), chat.get("title") or chat.get("username"))
for chat_id, (kind, title) in chats.items():
    print(f"  {chat_id}\t{kind}\t{title}")
if not chats:
    print("  (no updates - add the bot to the group and send a message, then retry)")
'
  exit 0
fi

if [ -z "${TELEGRAM_CHAT_ID}" ]; then
  echo "❌ TELEGRAM_CHAT_ID is empty. Set it in ${ENV_FILE} (see --chat-ids)" >&2
  exit 1
fi

# Keep Alertmanager's token file in sync with .env (never tracked by git)
mkdir -p "$(dirname "${SECRET_FILE}")"
if [ ! -f "${SECRET_FILE}" ] || [ "$(cat "${SECRET_FILE}")" != "${TELEGRAM_BOT_TOKEN}" ]; then
  (umask 077 && printf '%s' "${TELEGRAM_BOT_TOKEN}" > "${SECRET_FILE}")
  echo "🔐 Wrote ${SECRET_FILE#${ROOT_DIR}/}"
fi

MESSAGE="${1:-✅ MLOps tutorial07: test Telegram alert từ $(hostname) lúc $(date '+%Y-%m-%d %H:%M:%S %Z')}"

RESPONSE="$(curl -sS --max-time 15 -X POST "${API}/sendMessage" \
  --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
  --data-urlencode "text=${MESSAGE}")"

if echo "${RESPONSE}" | grep -q '"ok":true'; then
  MESSAGE_ID="$(echo "${RESPONSE}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["result"]["message_id"])')"
  echo "✅ Sent test message to chat ${TELEGRAM_CHAT_ID} (message_id=${MESSAGE_ID})"
else
  echo "❌ Telegram API error: ${RESPONSE}" >&2
  echo "   If 'chat not found' or the group was upgraded to a supergroup (-100...), run: $0 --chat-ids" >&2
  exit 1
fi
