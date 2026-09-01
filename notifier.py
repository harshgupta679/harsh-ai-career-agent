import os
import requests
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_alert(company: str, position: str, score: float, status_msg: str, apply_link: str = "", job_id: str = ""):
    """Sends rich job alert with 1-Click Auto Apply Inline Button, separating System Pings from Real Jobs."""
    if not BOT_TOKEN or not CHAT_ID:
        print("[TELEGRAM] Bot Token or Chat ID is missing.")
        return

    # 1. System Health / Heartbeat Ping (NO Buttons attached)
    if job_id in ["status_ping", "heartbeat"] or company == "System Monitor":
        health_text = (
            f"🟢 *AI AGENT SYSTEM STATUS*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⚙️ *Service:* Render 24/7 Keep-Alive\n"
            f"📌 *Health:* Online & Monitoring\n"
            f"{status_msg}"
        )
        payload = {
            "chat_id": CHAT_ID,
            "text": health_text,
            "parse_mode": "Markdown"
        }
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            requests.post(url, json=payload, timeout=10)
        except Exception as e:
            print(f"[TELEGRAM HEALTH PING ERROR] {e}")
        return

    # 2. Real Job Alert (With Action Buttons)
    text = (
        f"🎯 *AI Career Agent Alert*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🏢 *Company:* {company}\n"
        f"💼 *Position:* {position}\n"
        f"📊 *ATS Match Score:* `{score}%`\n"
        f"📌 *Status:* {status_msg}\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )

    inline_keyboard = []
    action_row = []

    if job_id:
        action_row.append({"text": "⚡ 1-Click Auto Apply", "callback_data": f"apply_{job_id}"})

    if apply_link and apply_link.startswith("http") and not apply_link.endswith("onrender.com"):
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