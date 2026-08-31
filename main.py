import time
import uuid
import schedule
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
from telegram_bot import register_job_for_interaction

# Optional Playwright Easy Apply integration
try:
    from playwright_applier import LinkedInEasyApplyAgent
    PLAYWRIGHT_INSTALLED = True
except ImportError:
    PLAYWRIGHT_INSTALLED = False

# Initialize SQLite database
database.init_db()

def process_scouted_job(job: dict):
    company = job["company"]
    position = job["position"]
    apply_link = job.get("apply_link", "")

    # 1. Anti-Spam / Prevent Duplicate Applications
    if database.is_already_applied(company, position):
        print(f"[SKIPPED] {company} - {position}: Already processed in database.")
        return

    # 2. ATS Match & Skill Gap Evaluation (Gemini 2.5 Flash)
    eval_result = MatchmakerAgent.evaluate_job(position, job["description"])

    # 3. Filter by Match Score (>= 65%)
    if not eval_result.apply_verdict or eval_result.match_score < 65.0:
        print(f"[REJECTED] {company} - {position} | Score: {eval_result.match_score}% | Missing: {eval_result.missing_skills}")
        database.log_skill_gap(position, company, eval_result.missing_skills)
        return

    # 4. Generate Interactive Job ID for Telegram Remote Control
    job_id = str(uuid.uuid4())[:8]
    register_job_for_interaction(job_id, {
        "company": company,
        "position": position,
        "apply_link": apply_link,
        "role": eval_result.selected_role
    })

    # 5. Method A: Direct Cold Email Outreach (with PDF Resume Attachment)
    recruiter_email = job.get("recruiter_email")
    if SecurityVerificationAgent.validate_contact_email(recruiter_email):
        sent = ApplicationAgent.dispatch_email_application(
            company=company,
            position=position,
            recipient_email=recruiter_email,
            job_description=job["description"],
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
            print(f"[APPLIED VIA EMAIL] Sent {eval_result.selected_role} application to {company} ({recruiter_email}) - Score: {eval_result.match_score}%")
            send_telegram_alert(company, position, eval_result.match_score, "Cold Email Dispatched + Resume Attached ✉️", apply_link, job_id)
            return

    # 6. Method B: Telegram 1-Click Remote Trigger & Easy Apply Alert
    database.log_application(
        company=company,
        position=position,
        platform="LinkedIn 1-Click",
        email="N/A",
        role=eval_result.selected_role,
        score=eval_result.match_score
    )
    print(f"[MATCH FOUND] {company} - {position} qualifies ({eval_result.match_score}%). Alerting Telegram.")
    send_telegram_alert(company, position, eval_result.match_score, "Qualified Match (Tap below to Auto-Apply) ⚡", apply_link, job_id)

def run_job_scout_pipeline():
    print(f"\n==========================================")
    print(f"Running Job Pipeline: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"==========================================")
    
    live_jobs = fetch_live_jobs()
    print(f"Scouted {len(live_jobs)} fresh listings.")
    
    for job in live_jobs:
        process_scouted_job(job)

# ----------------- SCHEDULER -----------------
# Scout every 2 hours for fresh postings
schedule.every(2).hours.do(run_job_scout_pipeline)

# Email monthly market report every 30 days
schedule.every(30).days.do(AnalyticsAgent.generate_and_send_monthly_report)

if __name__ == "__main__":
    print("AI Career Agent Master Pipeline Initialized...")
    
    # Run immediate first cycle on startup
    run_job_scout_pipeline()

    # Continuous background listener
    while True:
        schedule.run_pending()
        time.sleep(30)