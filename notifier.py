import os
import requests
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_alert(company: str, position: str, score: float, status: str, apply_link: str = ""):
    """Sends real-time job application updates straight to your Telegram phone app."""
    if not BOT_TOKEN or not CHAT_ID:
        print("[TELEGRAM] Missing Bot Token or Chat ID in .env")
        return

    text = f"""🚀 *AI Career Agent Alert*
━━━━━━━━━━━━━━━━━━
🏢 *Company:* {company}
💼 *Role:* {position}
🎯 *Match Score:* {score}%
📊 *Status:* {status}
🔗 [Job Application Link]({apply_link})
━━━━━━━━━━━━━━━━━━"""

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            print(f"[TELEGRAM API ERROR] Status {response.status_code}: {response.text}")
    except Exception as e:
        print(f"[TELEGRAM NETWORK ERROR] {e}")