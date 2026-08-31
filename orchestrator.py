import os
import time
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
from playwright_applier import LinkedInEasyApplyAgent

# Initialize DB
database.init_db()

# ==========================================
# 1. DUMMY HTTP SERVER (Keeps Render Free Tier Alive)
# ==========================================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"AI Career Agent is running 24/7.")

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

    # Duplicate Guard
    if database.is_already_applied(company, position):
        return

    # ATS Match & Evaluation
    eval_result = MatchmakerAgent.evaluate_job(position, job["description"])

    # Filter Non-Matching Jobs (< 65%)
    if not eval_result.apply_verdict or eval_result.match_score < 65.0:
        database.log_skill_gap(position, company, eval_result.missing_skills)
        return

    # Method A: Cold Outreach Email
    recruiter_email = job.get("recruiter_email")
    if SecurityVerificationAgent.validate_contact_email(recruiter_email):
        try:
            ApplicationAgent.dispatch_email_application(
                company=company,
                position=position,
                recipient_email=recruiter_email,
                role_type=eval_result.selected_role
            )
            database.log_application(
                company=company,
                position=position,
                platform="Direct Email",
                email=recruiter_email,
                role=eval_result.selected_role,
                score=eval_result.match_score
            )
            print(f"[APPLIED VIA EMAIL] {company} - {position}")
            send_telegram_alert(company, position, eval_result.match_score, "Applied via Direct Email ✅", apply_link)
            return
        except Exception as e:
            print(f"[EMAIL ERROR] {e}")

    # Method B: LinkedIn Application
    database.log_application(
        company=company,
        position=position,
        platform="LinkedIn Opportunity",
        email="N/A",
        role=eval_result.selected_role,
        score=eval_result.match_score
    )
    print(f"[MATCH FOUND] Alerting for {company} - {position}")
    send_telegram_alert(company, position, eval_result.match_score, "Qualified Opportunity (Ready to Apply) 🎯", apply_link)

def run_job_scout_pipeline():
    print(f"\n--- Running Job Scout Pipeline: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
    live_jobs = fetch_live_jobs()
    print(f"Scouted {len(live_jobs)} live postings.")
    for job in live_jobs:
        process_scouted_job(job)

# Execution Schedule
schedule.every(2).hours.do(run_job_scout_pipeline)
schedule.every(30).days.do(AnalyticsAgent.generate_and_send_monthly_report)

if __name__ == "__main__":
    print("AI Career Agent Pipeline Active on Cloud...")
    
    # Start Keep-Alive Server in background thread
    server_thread = threading.Thread(target=run_health_server, daemon=True)
    server_thread.start()
    
    # Run first round immediately
    run_job_scout_pipeline()
    
    # 24x7 Continuous Loop
    while True:
        schedule.run_pending()
        time.sleep(60)