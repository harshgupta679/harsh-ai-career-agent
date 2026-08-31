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
from telegram_bot import register_job_for_interaction, listen_for_telegram_clicks

# Initialize DB
database.init_db()

# ==========================================
# 1. 24/7 KEEP-ALIVE SERVER (For Render)
# ==========================================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"AI Career Agent & Telegram Controller Active 24/7.")

def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

# ==========================================
# 2. JOB PROCESSING PIPELINE
# ==========================================
def process_scouted_job(job: dict):
    company = job["company"]
    position = job["position"]
    apply_link = job.get("apply_link", "")
    description = job.get("description", "")

    # Duplicate Guard
    if database.is_already_applied(company, position):
        return

    # ATS Match & Evaluation (Gemini 2.5 Flash)
    eval_result = MatchmakerAgent.evaluate_job(position, description)

    # Filter Non-Matching Jobs (< 65%)
    if not eval_result.apply_verdict or eval_result.match_score < 65.0:
        database.log_skill_gap(position, company, eval_result.missing_skills)
        return

    # Register Job for 1-Click Remote Trigger
    job_id = str(uuid.uuid4())[:8]
    register_job_for_interaction(job_id, {
        "company": company,
        "position": position,
        "apply_link": apply_link,
        "role": eval_result.selected_role
    })

    # Method A: Cold Outreach Email (If genuine recruiter email exists)
    recruiter_email = job.get("recruiter_email")
    if SecurityVerificationAgent.validate_contact_email(recruiter_email):
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
                    email=recruiter_email,
                    role=eval_result.selected_role,
                    score=eval_result.match_score
                )
                print(f"[APPLIED VIA EMAIL] {company} - {position}")
                send_telegram_alert(company, position, eval_result.match_score, "Cold Email Dispatched + Resume Attached ✉️", apply_link, job_id)
                return
        except Exception as e:
            print(f"[EMAIL ERROR] {e}")

    # Method B: LinkedIn 1-Click Remote Apply Alert
    database.log_application(
        company=company,
        position=position,
        platform="LinkedIn 1-Click",
        email="N/A",
        role=eval_result.selected_role,
        score=eval_result.match_score
    )
    print(f"[MATCH FOUND] Alerting for {company} - {position}")
    send_telegram_alert(company, position, eval_result.match_score, "Qualified Opportunity (Tap below to Auto-Apply) ⚡", apply_link, job_id)

def run_job_scout_pipeline():
    print(f"\n--- Running Job Scout Pipeline: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
    live_jobs = fetch_live_jobs()
    print(f"Scouted {len(live_jobs)} live postings.")
    for job in live_jobs:
        process_scouted_job(job)

# Execution Schedules
schedule.every(2).hours.do(run_job_scout_pipeline)
schedule.every(30).days.do(AnalyticsAgent.generate_and_send_monthly_report)

if __name__ == "__main__":
    print("=== AI Career Agent Unified Pipeline Active ===")
    
    # 1. Start Keep-Alive Server Thread (Render 24/7)
    threading.Thread(target=run_health_server, daemon=True).start()
    
    # 2. Start Telegram 1-Click Button Listener Thread
    threading.Thread(target=listen_for_telegram_clicks, daemon=True).start()
    
    # 3. Run first job scout round immediately
    run_job_scout_pipeline()
    
    # 4. Continuous Loop
    while True:
        schedule.run_pending()
        time.sleep(30)