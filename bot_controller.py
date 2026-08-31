import os
import time
import requests
from dotenv import load_dotenv
from playwright_applier import LinkedInEasyApplyAgent

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# In-memory storage to link Telegram button taps to job data
ACTIVE_JOBS = {}

def send_interactive_job_card(job_id: str, company: str, position: str, score: float, apply_link: str, role_type: str = "Data Analyst"):
    """Sends job alert with 1-Click Auto Apply button and caches job metadata."""
    if not BOT_TOKEN or not CHAT_ID:
        print("[BOT CONTROLLER] Missing Telegram credentials.")
        return

    # Cache job data for callback action
    ACTIVE_JOBS[job_id] = {
        "company": company,
        "position": position,
        "apply_link": apply_link,
        "role_type": role_type
    }

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": (
            f"🎯 *New Job Match ({score}%)*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🏢 *Company:* {company}\n"
            f"💼 *Role:* {position}\n"
            f"📄 *Selected Profile:* `{role_type}`\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        ),
        "parse_mode": "Markdown",
        "reply_markup": {
            "inline_keyboard": [
                [{"text": "⚡ 1-Click Auto Apply", "callback_data": f"apply:{job_id}"}],
                [{"text": "🔗 Open Listing", "url": apply_link}]
            ]
        }
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"[BOT CONTROLLER ERROR] Failed to send job card: {e}")

def send_message(chat_id: str, text: str):
    """Utility helper to send plain or markdown updates."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})

def start_telegram_listener():
    """Continuously listens for user button clicks on Telegram."""
    if not BOT_TOKEN:
        print("[BOT CONTROLLER] Telegram Bot Token not configured.")
        return

    last_update_id = 0
    print("[BOT CONTROLLER] Telegram 1-Click Remote Listener Active...")

    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
            params = {"offset": last_update_id + 1, "timeout": 20}
            res = requests.get(url, params=params, timeout=25).json()

            if res.get("ok"):
                for update in res.get("result", []):
                    last_update_id = update["update_id"]

                    # Detect Inline Button Click
                    if "callback_query" in update:
                        cb = update["callback_query"]
                        cb_data = cb.get("data", "")
                        cb_id = cb.get("id")
                        user_chat_id = cb["message"]["chat"]["id"]

                        # Acknowledge button press immediately
                        requests.post(
                            f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery",
                            json={"callback_query_id": cb_id}
                        )

                        if cb_data.startswith("apply:"):
                            job_id = cb_data.split("apply:")[1]
                            job = ACTIVE_JOBS.get(job_id)

                            if job:
                                send_message(
                                    user_chat_id,
                                    f"⏳ *Auto-Applying to {job['company']} for {job['position']}...*\n_Launching browser & attaching matching resume..._"
                                )

                                # Trigger Playwright Browser Automation with Dynamic Resume
                                applied = LinkedInEasyApplyAgent.apply_to_job(
                                    job_url=job["apply_link"],
                                    role_type=job["role_type"]
                                )

                                if applied:
                                    send_message(
                                        user_chat_id,
                                        f"✅ *Application Submitted Successfully!* 🎉\n🏢 *Company:* {job['company']}\n💼 *Role:* {job['position']}"
                                    )
                                else:
                                    send_message(
                                        user_chat_id,
                                        f"⚠️ *Submission required external portal steps or verification.*\n🔗 [Complete application manually]({job['apply_link']})"
                                    )
                            else:
                                send_message(user_chat_id, "⚠️ This job interaction has expired.")
        except Exception as e:
            time.sleep(3)

        time.sleep(1)