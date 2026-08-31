import time
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

database.init_db()

def process_scouted_job(job: dict):
    company = job["company"]
    position = job["position"]
    apply_link = job.get("apply_link", "")

    # 1. Freshness Check (< 48 Hours)
    if not SecurityVerificationAgent.verify_job_freshness(job["posted_at"]):
        return

    # 2. Anti-Spam / Duplicate Guard
    if database.is_already_applied(company, position):
        return

    # 3. ATS Match & Skill Gap Analysis
    eval_result = MatchmakerAgent.evaluate_job(position, job["description"])

    # 4. Filter Non-Matching Jobs (< 65%)
    if not eval_result.apply_verdict or eval_result.match_score < 65.0:
        database.log_skill_gap(position, company, eval_result.missing_skills)
        return

    # 5. Method A: Dispatch Cold Email Outreach
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
            send_telegram_alert(company, position, eval_result.match_score, "Applied via Email", apply_link)
            return
        except Exception as e:
            print(f"[EMAIL ERROR] {e}")

    # 6. Method B: Direct Qualified Opportunity Found
    database.log_application(
        company=company,
        position=position,
        platform="Direct Link",
        email="N/A",
        role=eval_result.selected_role,
        score=eval_result.match_score
    )
    print(f"[MATCH ALERT SENT] {company} - {position} (Score: {eval_result.match_score}%)")
    send_telegram_alert(company, position, eval_result.match_score, "Matched - Ready for Easy Apply", apply_link)

def run_job_scout_pipeline():
    print(f"\n--- Running Job Scout Pipeline: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
    live_jobs = fetch_live_jobs()
    print(f"Discovered {len(live_jobs)} fresh listings.")
    for job in live_jobs:
        process_scouted_job(job)

schedule.every(3).hours.do(run_job_scout_pipeline)
schedule.every(30).days.do(AnalyticsAgent.generate_and_send_monthly_report)

if __name__ == "__main__":
    print("AI Career Agent Pipeline Active with Telegram Alerts...")
    run_job_scout_pipeline()
    while True:
        schedule.run_pending()
        time.sleep(60)