import os
import time
import requests
from dotenv import load_dotenv
from playwright_applier import LinkedInEasyApplyAgent

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
PENDING_JOBS = {}  # In-memory storage for active job actions

def register_job_for_interaction(job_id: str, job_data: dict):
    """Stores job metadata so Telegram callback can trigger application."""
    PENDING_JOBS[job_id] = job_data

def send_reply(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})

def listen_for_telegram_clicks():
    """Continuously listens for user button clicks on Telegram."""
    if not BOT_TOKEN:
        return

    last_update_id = 0
    print("[TELEGRAM CONTROLLER] Listening for 1-Click Apply button interactions...")

    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
            params = {"offset": last_update_id + 1, "timeout": 20}
            res = requests.get(url, params=params, timeout=25).json()

            if res.get("ok"):
                for update in res.get("result", []):
                    last_update_id = update["update_id"]

                    # Handle Button Click (Callback Query)
                    if "callback_query" in update:
                        cb = update["callback_query"]
                        cb_data = cb.get("data", "")
                        cb_id = cb.get("id")
                        user_chat_id = cb["message"]["chat"]["id"]

                        # Acknowledge Telegram callback popup
                        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id": cb_id})

                        if cb_data.startswith("apply:"):
                            target_id = cb_data.split("apply:")[1]
                            job = PENDING_JOBS.get(target_id)

                            if job:
                                send_reply(user_chat_id, f"⏳ *Applying automatically to {job['company']} for {job['position']}...*\n_Opening browser and uploading resume..._")
                                
                                # Trigger Playwright Browser Automation
                                success = LinkedInEasyApplyAgent.apply_to_job(job["apply_link"], role_type=job.get("role", "Data Analyst"))
                                
                                if success:
                                    send_reply(user_chat_id, f"✅ *Application Successfully Submitted!* 🎉\n🏢 *Company:* {job['company']}\n💼 *Role:* {job['position']}")
                                else:
                                    send_reply(user_chat_id, f"⚠️ *Direct form submission required extra inputs or verification.*\n🔗 [Click here to complete final step manually]({job['apply_link']})")
                            else:
                                send_reply(user_chat_id, "⚠️ Job session expired or already processed.")

        except Exception as e:
            time.sleep(3)

        time.sleep(1)