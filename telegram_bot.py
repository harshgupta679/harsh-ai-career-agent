import os
import time
import sqlite3
import requests
from dotenv import load_dotenv
from playwright_applier import LinkedInEasyApplyAgent

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
PENDING_JOBS = {}  # In-memory fast cache

DB_PATH = os.path.abspath("career_agent.db")

def register_job_for_interaction(job_id: str, job_data: dict):
    """Stores job metadata in memory for quick action."""
    PENDING_JOBS[str(job_id)] = job_data

def get_job_from_db_or_cache(job_id: str) -> dict:
    """Retrieves job metadata from cache or persistent SQLite database."""
    job = PENDING_JOBS.get(str(job_id))
    if job:
        return job

    # Fallback to database so buttons work even after server redeploy/restart
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT company_name, position, job_url, applied_resume_role FROM applications ORDER BY id DESC LIMIT 20"
        )
        rows = cursor.fetchall()
        conn.close()

        for company, position, url, role in rows:
            calc_id = f"{abs(hash(url)) % 1000000}"
            if calc_id == str(job_id) or str(job_id) in url:
                return {
                    "company": company,
                    "position": position,
                    "apply_link": url,
                    "role": role or "Data Analyst"
                }
    except Exception as e:
        print(f"[DB RETRIEVAL ERROR] {e}")

    return None

def send_reply(chat_id, text):
    """Sends a markdown reply back to Telegram."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}, timeout=10)
    except Exception as e:
        print(f"[TELEGRAM SEND ERROR] {e}")

def listen_for_telegram_clicks():
    """Continuously listens for 1-Click Apply callback buttons on Telegram."""
    if not BOT_TOKEN:
        print("[TELEGRAM CONTROLLER] Missing TELEGRAM_BOT_TOKEN.")
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

                    # Handle Callback Button Click
                    if "callback_query" in update:
                        cb = update["callback_query"]
                        cb_data = cb.get("data", "")
                        cb_id = cb.get("id")
                        user_chat_id = cb["message"]["chat"]["id"]

                        # Acknowledge callback immediately to clear loading state on user device
                        try:
                            requests.post(
                                f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery",
                                json={"callback_query_id": cb_id},
                                timeout=5
                            )
                        except Exception:
                            pass

                        # Support both apply_ and apply: formats
                        if cb_data.startswith("apply_") or cb_data.startswith("apply:"):
                            target_id = cb_data.replace("apply_", "").replace("apply:", "").strip()
                            job = get_job_from_db_or_cache(target_id)

                            if job:
                                send_reply(
                                    user_chat_id, 
                                    f"⏳ *Applying automatically to {job['company']} for {job['position']}...*\n_Opening headless browser and preparing resume submission..._"
                                )

                                # Trigger Playwright Browser Automation
                                role_target = job.get("role", "Data Analyst")
                                success = LinkedInEasyApplyAgent.apply_to_job(job["apply_link"], role_type=role_target)

                                if success:
                                    send_reply(
                                        user_chat_id, 
                                        f"✅ *Application Successfully Submitted!* 🎉\n🏢 *Company:* {job['company']}\n💼 *Role:* {job['position']}"
                                    )
                                else:
                                    send_reply(
                                        user_chat_id, 
                                        f"⚠️ *Direct form submission required manual inputs or verification.*\n🔗 [Click here to complete application manually]({job['apply_link']})"
                                    )
                            else:
                                send_reply(
                                    user_chat_id, 
                                    "⚠️ *Job details not found in active session.*\nPlease click *🔗 View Job* directly to apply."
                                )

        except Exception as e:
            time.sleep(3)

        time.sleep(1)