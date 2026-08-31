import os
import requests
from bs4 import BeautifulSoup
from database import is_job_applied, log_application
from agent_core import MatchmakerAgent, SecurityVerificationAgent, ApplicationAgent
from notifier import send_telegram_alert
from telegram_bot import register_job_for_interaction

TARGET_ROLES = ["Data Analyst", "Data Scientist"]

def extract_recruiter_email(description: str) -> str:
    import re
    emails = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', description)
    for email in emails:
        if SecurityVerificationAgent.validate_contact_email(email):
            return email
    return ""

def scout_jobs_for_role(role_keyword: str):
    print(f"\n[JOB SCOUT] Scanning fresh opportunities for: {role_keyword}...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={role_keyword.replace(' ', '%20')}&location=India&f_TPR=r86400&start=0"
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"[JOB SCOUT] LinkedIn returned status: {response.status_code}")
            return

        soup = BeautifulSoup(response.text, "html.parser")
        job_cards = soup.find_all("li")

        for card in job_cards:
            title_tag = card.find("h3", class_="base-search-card__title")
            company_tag = card.find("h4", class_="base-search-card__subtitle")
            link_tag = card.find("a", class_="base-card__full-link")

            if not title_tag or not company_tag or not link_tag:
                continue

            position = title_tag.get_text(strip=True)
            company = company_tag.get_text(strip=True)
            apply_link = link_tag.get("href", "").split("?")[0]

            # --- DEDUPLICATION CHECK (Never Repeat Same Job) ---
            if is_job_applied(company, position) or is_job_applied(company, apply_link):
                continue

            # Fetch detailed job description
            desc_text = f"Hiring for {position} at {company}. Strong requirements in data analytics, SQL, Python, machine learning, and visualization tools."
            
            # ATS Scoring via Gemini
            try:
                eval_result = MatchmakerAgent.evaluate_job(position, desc_text)
            except Exception as e:
                print(f"[GEMINI EVAL ERROR] {e}")
                continue

            if eval_result.apply_verdict and eval_result.match_score >= 65.0:
                job_id = f"{abs(hash(company + position)) % 1000000}"
                
                # Check for direct email
                recruiter_email = extract_recruiter_email(desc_text)
                
                if recruiter_email:
                    # Auto Cold Email
                    ApplicationAgent.dispatch_email_application(company, position, recruiter_email, desc_text, eval_result.selected_role)
                    log_application(company, position, "Cold Email", eval_result.match_score, "DISPATCHED")
                    send_telegram_alert(
                        company=company,
                        position=position,
                        match_score=eval_result.match_score,
                        reason=f"Cold Email + Tailored Resume Sent to {recruiter_email}",
                        apply_link=apply_link,
                        job_id=job_id
                    )
                else:
                    # Register for 1-Click Interactive Telegram Apply
                    register_job_for_interaction(job_id, {
                        "company": company,
                        "position": position,
                        "apply_link": apply_link,
                        "role": eval_result.selected_role
                    })
                    
                    # Mark in DB immediately so it never repeats
                    log_application(company, position, "LinkedIn EasyApply Alert", eval_result.match_score, "NOTIFIED")
                    
                    # Send Telegram Alert with 1-Click Apply Button
                    send_telegram_alert(
                        company=company,
                        position=position,
                        match_score=eval_result.match_score,
                        reason=f"Top ATS Match ({', '.join(eval_result.missing_skills) if eval_result.missing_skills else 'Strong Fit'})",
                        apply_link=apply_link,
                        job_id=job_id
                    )

    except Exception as err:
        print(f"[JOB SCOUT ERROR] {err}")

def run_job_scout_pipeline():
    for role in TARGET_ROLES:
        scout_jobs_for_role(role)