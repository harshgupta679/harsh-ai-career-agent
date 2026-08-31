import os
import requests
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_alert(company: str, position: str, score: float, status_msg: str, apply_link: str = "", job_id: str = ""):
    """Sends rich job alert with 1-Click Auto Apply Inline Button."""
    if not BOT_TOKEN or not CHAT_ID:
        print("[TELEGRAM] Bot Token or Chat ID is missing.")
        return

    text = (
        f"🤖 *AI Career Agent Alert*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🏢 *Company:* {company}\n"
        f"💼 *Position:* {position}\n"
        f"📊 *ATS Match Score:* `{score}%`\n"
        f"📌 *Status:* {status_msg}\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )

    # Inline Buttons Setup
    inline_keyboard = []
    action_row = []

    if apply_link and apply_link.startswith("http"):
        # 1-Click Auto Apply Button (passes apply_link via callback)
        callback_payload = f"apply:{job_id}" if job_id else f"apply_direct"
        action_row.append({"text": "⚡ 1-Click Auto Apply", "callback_data": callback_payload})
        action_row.append({"text": "🔗 View Job", "url": apply_link})

    if action_row:
        inline_keyboard.append(action_row)

    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "reply_markup": {"inline_keyboard": inline_keyboard} if inline_keyboard else {}
    }

    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            print(f"[TELEGRAM ERROR] {response.text}")
    except Exception as e:
        print(f"[TELEGRAM NETWORK ERROR] {e}")