import os
import re
import json
import smtplib
from datetime import datetime, timedelta
from typing import List, Literal, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from google import genai
from google.genai import types
import database

load_dotenv()

# Initialize Gemini Client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Personal Configuration
CANDIDATE_NAME = "Harsh Gupta"
CANDIDATE_PHONE = "+91 7906936146"
LINKEDIN_URL = "https://www.linkedin.com/in/harsh-gupta-09031830a/"
MONTHLY_REPORT_EMAIL = os.getenv("MONTHLY_REPORT_RECEIVER", "cryptomarketanalysis12@gmail.com")

RESUME_MAP = {
    "Data Analyst": "Harsh_Gupta_Resume_DataAnalyst.pdf",
    "Data Scientist": "Harsh_Gupta_Resume_DataScientist.pdf"
}

class JobMatchEvaluation(BaseModel):
    selected_role: Literal["Data Analyst", "Data Scientist", "None"] = "None"
    match_score: float = 0.0
    apply_verdict: bool = False
    missing_skills: List[str] = []
    match_reasoning: str = ""

# ==========================================
# 1. CYBERSECURITY & VERIFICATION AGENT
# ==========================================
class SecurityVerificationAgent:
    @staticmethod
    def verify_job_freshness(posted_date: datetime) -> bool:
        """Enforces the strict 48-hour freshness rule."""
        cutoff = datetime.now() - timedelta(hours=48)
        return posted_date >= cutoff

    @staticmethod
    def sanitize_text(text: str) -> str:
        """Strips injection payloads and unwanted HTML characters."""
        text = re.sub(r"<[^>]*>", "", text)
        for injection in ["DROP TABLE", "--", "UNION SELECT", "exec("]:
            text = text.replace(injection, "")
        return text.strip()

    @staticmethod
    def validate_contact_email(email: Optional[str]) -> bool:
        """Ensures the destination email is genuine and formatted correctly."""
        if not email:
            return False
        pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        return bool(re.match(pattern, email))

# ==========================================
# 2. ATS MATCHMAKER & DECISION AGENT
# ==========================================
class MatchmakerAgent:
    @staticmethod
    def evaluate_job(job_title: str, job_description: str) -> JobMatchEvaluation:
        clean_title = SecurityVerificationAgent.sanitize_text(job_title)
        clean_jd = SecurityVerificationAgent.sanitize_text(job_description)

        prompt = f"""
        You are an ATS Matchmaker. Analyze this job description for Harsh Gupta.
        Candidate Profile:
        - B.Tech IT (Bharat Institute of Technology)
        - Targeted Roles: Data Analyst, Data Scientist
        - Core Skills: Python, SQL, Pandas, NumPy, Scikit-learn, Matplotlib, Data Cleaning, EDA, Statistical Modeling, Anomaly Detection
        - Secondary / Learning: Power BI, Tableau, GCP

        Job Title: {clean_title}
        Job Description: {clean_jd}

        Return a valid JSON object ONLY with these exact keys:
        {{
            "selected_role": "Data Analyst" or "Data Scientist" or "None",
            "match_score": <float between 0.0 and 100.0>,
            "apply_verdict": <true if match_score >= 65.0 else false>,
            "missing_skills": ["skill1", "skill2"],
            "match_reasoning": "brief summary"
        }}
        """

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            data = json.loads(response.text)
            return JobMatchEvaluation(**data)
        except Exception:
            # Safe Fallback Rule Engine
            title_lower = clean_title.lower()
            if "data analyst" in title_lower or "business analyst" in title_lower:
                return JobMatchEvaluation(
                    selected_role="Data Analyst",
                    match_score=85.0,
                    apply_verdict=True,
                    missing_skills=[],
                    match_reasoning="Strong alignment with Data Analyst skill profile."
                )
            elif "data scientist" in title_lower or "machine learning" in title_lower:
                return JobMatchEvaluation(
                    selected_role="Data Scientist",
                    match_score=80.0,
                    apply_verdict=True,
                    missing_skills=[],
                    match_reasoning="Alignment with Python and Statistical modeling skillset."
                )
            return JobMatchEvaluation(
                selected_role="None",
                match_score=40.0,
                apply_verdict=False,
                missing_skills=["Role specific tech stack"],
                match_reasoning="Role title out of targeted scope."
            )

# ==========================================
# 3. APPLICATION & OUTREACH AGENT
# ==========================================
class ApplicationAgent:
    @staticmethod
    def dispatch_email_application(company: str, position: str, recipient_email: str, role_type: str):
        from email.message import EmailMessage
        
        sender_email = os.getenv("SENDER_EMAIL")
        app_pwd = os.getenv("EMAIL_APP_PASSWORD")
        resume_filename = RESUME_MAP.get(role_type)

        msg = EmailMessage()
        msg['Subject'] = f"Application for {position} - {CANDIDATE_NAME}"
        msg['From'] = sender_email
        msg['To'] = recipient_email

        body = f"""Dear Hiring Team at {company},

I am writing to express my strong interest in the {position} role.

I am a final-year B.Tech Information Technology student with practical experience building automated data transformation pipelines, exploratory data analysis, and statistical anomaly detection models using Python and SQL.

Key Highlights:
- Engineered automated data pipelines cutting manual processing effort by ~40%.
- Preprocessed and modeled 10,000+ records with rigorous statistical data validation.
- Tech Stack: Python (Pandas, NumPy, Scikit-learn), SQL, EDA & Predictive Modeling.

LinkedIn: {LINKEDIN_URL}
My {role_type} resume is attached for your review. I look forward to the opportunity to discuss my application.

Best regards,
{CANDIDATE_NAME}
Phone: {CANDIDATE_PHONE}
"""
        msg.set_content(body)

        if resume_filename and os.path.exists(resume_filename):
            with open(resume_filename, "rb") as f:
                msg.add_attachment(f.read(), maintype="application", subtype="pdf", filename=resume_filename)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(sender_email, app_pwd)
            smtp.send_message(msg)

# ==========================================
# 4. MONTHLY ANALYTICS & LEARNING AGENT
# ==========================================
class AnalyticsAgent:
    @staticmethod
    def generate_and_send_monthly_report():
        import sqlite3
        conn = sqlite3.connect(database.DB_NAME)
        cursor = conn.cursor()

        one_month_ago = datetime.now() - timedelta(days=30)
        cursor.execute("SELECT company_name, position, platform, match_score, applied_at FROM applications WHERE applied_at >= ?", (one_month_ago,))
        apps = cursor.fetchall()

        cursor.execute("SELECT missing_skills FROM skill_gap_logs WHERE recorded_at >= ?", (one_month_ago,))
        gaps = cursor.fetchall()
        conn.close()

        skill_counts = {}
        for row in gaps:
            skills = [s.strip() for s in row[0].split(",") if s.strip()]
            for s in skills:
                skill_counts[s] = skill_counts.get(s, 0) + 1

        synthesis_prompt = f"""
        Candidate: {CANDIDATE_NAME}
        Monthly Cycle: Last 30 Days
        Total Applications Submitted: {len(apps)}
        Missing Skill Frequency Across Analyzed Market Roles: {skill_counts}

        Generate a high-level monthly intelligence report:
        1. Executive Summary of Application Activity.
        2. Market Demand Analysis (Top 3 Missing Skills to prioritize).
        3. Strategic Upskilling Roadmap.
        """

        try:
            report_md = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=synthesis_prompt
            ).text
        except Exception:
            report_md = f"Monthly Intelligence Summary: Total Applications: {len(apps)}. Missing Skill Logs: {skill_counts}"

        from email.message import EmailMessage
        sender_email = os.getenv("SENDER_EMAIL")
        app_pwd = os.getenv("EMAIL_APP_PASSWORD")

        msg = EmailMessage()
        msg['Subject'] = f"Autonomous Career Agent - Monthly Intelligence Report ({datetime.now().strftime('%B %Y')})"
        msg['From'] = sender_email
        msg['To'] = MONTHLY_REPORT_EMAIL
        msg.set_content(report_md)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(sender_email, app_pwd)
            smtp.send_message(msg)