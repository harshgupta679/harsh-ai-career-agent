import os
import time
import uuid
import threading
import schedule
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

import database
from job_scout import fetch_live_jobs
from agent_core import (
    SecurityVerificationAgent,
    MatchmakerAgent,
    ApplicationAgent,
    AnalyticsAgent
)
from notifier import send_telegram_alert
import telegram_bot

# Initialize Database
database.init_db()

# ==========================================
# 1. 24/7 HEALTH & KEEP-ALIVE SERVER
# ==========================================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"AI Career Agent & Telegram Controller Active 24/7.")

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()

    def log_message(self, format, *args):
        return

def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    print(f"[KEEP-ALIVE] Health check server listening on port {port}")
    server.serve_forever()

def start_telegram_listener():
    try:
        if hasattr(telegram_bot, "listen_for_telegram_clicks"):
            telegram_bot.listen_for_telegram_clicks()
        elif hasattr(telegram_bot, "run_bot_listener"):
            telegram_bot.run_bot_listener()
        elif hasattr(telegram_bot, "start_bot"):
            telegram_bot.start_bot()
    except Exception as err:
        print(f"[TELEGRAM CONTROLLER ERROR] {err}")

# ==========================================
# 2. JOB PROCESSING PIPELINE
# ==========================================
def process_scouted_job(job: dict):
    company = job["company"]
    position = job["position"]
    apply_link = job.get("apply_link", "")
    description = job.get("description", "")

    # Duplicate Guard
    if database.is_already_applied(company, position, apply_link):
        return

    # ATS Match & Evaluation
    try:
        eval_result = MatchmakerAgent.evaluate_job(position, description)
    except Exception as err:
        print(f"[EVALUATION ERROR] {company} - {position}: {err}")
        return

    # Filter Non-Matching Jobs (< 65%)
    if not eval_result.apply_verdict or eval_result.match_score < 65.0:
        database.log_skill_gap(position, company, eval_result.missing_skills)
        return

    # Register Job for 1-Click Remote Trigger
    job_id = str(uuid.uuid4())[:8]
    if hasattr(telegram_bot, "register_job_for_interaction"):
        telegram_bot.register_job_for_interaction(job_id, {
            "company": company,
            "position": position,
            "apply_link": apply_link,
            "role": eval_result.selected_role
        })

    # Method A: Cold Outreach Email
    recruiter_email = job.get("recruiter_email")
    if recruiter_email and SecurityVerificationAgent.validate_contact_email(recruiter_email):
        try:
            sent = ApplicationAgent.dispatch_email_application(
                company=company,
                position=position,
                recipient_email=recruiter_email,
                job_description=description,
                role_type=eval_result.selected_role
            )
            if sent:
                database.log_application(
                    company=company,
                    position=position,
                    platform="Direct Cold Email",
                    score=eval_result.match_score,
                    status="DISPATCHED",
                    job_url=apply_link,
                    email=recruiter_email,
                    role=eval_result.selected_role
                )
                print(f"[APPLIED VIA EMAIL] {company} - {position}")
                send_telegram_alert(company, position, eval_result.match_score, f"Cold Email Sent to {recruiter_email} ✉️", apply_link, job_id)
                return
        except Exception as e:
            print(f"[EMAIL ERROR] {e}")

    # Method B: LinkedIn 1-Click Remote Apply Alert
    database.log_application(
        company=company,
        position=position,
        platform="LinkedIn 1-Click",
        score=eval_result.match_score,
        status="NOTIFIED",
        job_url=apply_link,
        email="N/A",
        role=eval_result.selected_role
    )
    print(f"[MATCH FOUND] Alerting for {company} - {position}")
    send_telegram_alert(
        company=company,
        position=position,
        match_score=eval_result.match_score,
        reason=f"Top ATS Match ({eval_result.match_score}%) ⚡",
        apply_link=apply_link,
        job_id=job_id
    )

def run_job_scout_pipeline():
    print(f"\n--- Running Job Scout Pipeline: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
    live_jobs = fetch_live_jobs() or []
    print(f"Scouted {len(live_jobs)} live postings.")
    for job in live_jobs:
        process_scouted_job(job)

def run_delayed_first_scout():
    time.sleep(5)
    run_job_scout_pipeline()

# Schedules
schedule.every(2).hours.do(run_job_scout_pipeline)
schedule.every(30).days.do(AnalyticsAgent.generate_and_send_monthly_report)

if __name__ == "__main__":
    print("=== AI Career Agent Unified Pipeline Active ===")
    
    # 1. Telegram Listener Thread
    threading.Thread(target=start_telegram_listener, daemon=True).start()
    
    # 2. Delayed Initial Scout Thread
    threading.Thread(target=run_delayed_first_scout, daemon=True).start()
    
    # 3. Scheduler Background Worker
    def schedule_loop():
        while True:
            schedule.run_pending()
            time.sleep(15)

    threading.Thread(target=schedule_loop, daemon=True).start()

    # 4. Main Thread binds Keep-Alive Web Server
    run_health_server()