import os
import requests
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_alert(company: str = "", position: str = "", match_score: float = 0.0, reason: str = "", apply_link: str = "", job_id: str = "", *args, **kwargs) -> bool:
    """Dispatches formatted Telegram job notifications with interactive inline buttons."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[NOTIFIER ERROR] Telegram Bot Token or Chat ID not configured.")
        return False

    # Extract score or link if passed via alternate keyword names
    score = kwargs.get("score", match_score)
    link = kwargs.get("job_url", apply_link)
    jid = str(kwargs.get("id", job_id))

    # Formatting for Heartbeat vs Live Postings
    if jid in ["heartbeat", "status_ping"]:
        text = (
            f"🤖 <b>AI Career Agent Monitor</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🏢 <b>System:</b> {company}\n"
            f"💼 <b>Status:</b> {position}\n"
            f"📌 <b>Details:</b> {reason}\n"
        )
    else:
        text = (
            f"🤖 <b>AI Career Agent Alert</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🏢 <b>Company:</b> {company}\n"
            f"💼 <b>Position:</b> {position}\n"
            f"📊 <b>ATS Match Score:</b> {score}%\n"
            f"📌 <b>Status:</b> {reason}\n"
        )

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }

    # Inline Action Buttons
    if jid and jid not in ["heartbeat", "status_ping", ""]:
        payload["reply_markup"] = {
            "inline_keyboard": [
                [
                    {"text": "⚡ 1-Click Auto Apply", "callback_data": f"apply_{jid}"},
                    {"text": "🔗 View Job", "url": link if str(link).startswith("http") else "https://linkedin.com"}
                ]
            ]
        }
    elif link and str(link).startswith("http") and jid not in ["heartbeat", "status_ping"]:
        payload["reply_markup"] = {
            "inline_keyboard": [
                [
                    {"text": "🔗 View Link", "url": str(link)}
                ]
            ]
        }

    try:
        res = requests.post(url, json=payload, timeout=10)
        return res.status_code == 200
    except Exception as e:
        print(f"[NOTIFIER ERROR] Telegram request failed: {e}")
        return False