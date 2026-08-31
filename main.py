import os
import smtplib
import sqlite3
from email.message import EmailMessage
from datetime import datetime, timedelta
from dotenv import load_dotenv

from google import genai
from google.genai import types

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Candidate Details
CANDIDATE_NAME = "Harsh Gupta"
CANDIDATE_PHONE = "+91 7906936146"
LINKEDIN_URL = "https://www.linkedin.com/in/harsh-gupta-09031830a/"
RESUME_PATHS = {
    "Data Analyst": "Harsh_Gupta_Resume_DataAnalyst.pdf",
    "Data Scientist": "Harsh_Gupta_Resume_DataScientist.pdf"
}

# ----------------- SECURITY & VALIDATION AGENT -----------------
class SecurityAgent:
    @staticmethod
    def sanitize_input(text: str) -> str:
        """Strips injection payloads and suspicious script characters."""
        disallowed = ["<script>", "</script>", "DROP TABLE", "--", "exec("]
        for item in disallowed:
            text = text.replace(item, "")
        return text.strip()

    @staticmethod
    def is_valid_email(email: str) -> bool:
        """Validates genuine recruiter/company email address format."""
        import re
        regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        return bool(re.match(regex, email))

# ----------------- APPLICATION & MATCHING AGENT -----------------
class ApplicationAgent:
    @staticmethod
    def evaluate_fit(job_title: str, job_description: str):
        """Uses Gemini to score alignment, select resume, and identify skill gaps."""
        prompt = f"""
        You are an ATS Matchmaker. Analyze this job description for Harsh Gupta.
        Job Title: {job_title}
        Job Description: {job_description}

        Candidate Profile:
        - B.Tech IT (2022-2026), Bharat Institute of Technology
        - Roles Available: 'Data Analyst' or 'Data Scientist'
        - Skills: Python, SQL, Pandas, NumPy, Scikit-Learn, EDA, Data Pipelines, Anomaly Detection.
        - Learning: Power BI, Tableau, GCP.

        Respond in this exact YAML format:
        ROLE: <Data Analyst or Data Scientist or None>
        SCORE: <0 to 100>
        FIT: <YES or NO> (YES only if SCORE >= 65)
        MISSING_SKILLS: <comma-separated list of missing skills or None>
        """
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text

    @staticmethod
    def send_application_email(recipient_email: str, company: str, job_title: str, selected_role: str):
        """Builds custom cold outreach email and attaches the selected resume."""
        sender_email = os.getenv("SENDER_EMAIL")
        app_pwd = os.getenv("EMAIL_APP_PASSWORD")
        resume_file = RESUME_PATHS.get(selected_role)

        msg = EmailMessage()
        msg['Subject'] = f"Application for {job_title} Role - Harsh Gupta"
        msg['From'] = sender_email
        msg['To'] = recipient_email

        body = f"""Dear Hiring Team at {company},

I am writing to express my interest in the {job_title} position. 

I am a final-year B.Tech Information Technology student with practical experience building automated data transformation pipelines, exploratory data analysis, and statistical anomaly detection models using Python and SQL.

Key Highlights:
- Built automation scripts reducing data preprocessing time by ~40%.
- Engineered statistical anomaly models validating 10,000+ records.
- Technical Toolkit: Python (Pandas, NumPy, Scikit-Learn), SQL, Data Cleaning & EDA.

LinkedIn Profile: {LINKEDIN_URL}
My resume is attached for your review. I would welcome the opportunity to discuss how my skillset aligns with your team's objectives.

Best regards,
Harsh Gupta
{CANDIDATE_PHONE}
"""
        msg.set_content(body)

        # Attach corresponding resume
        if os.path.exists(resume_file):
            with open(resume_file, 'rb') as f:
                file_data = f.read()
                msg.add_attachment(file_data, maintype='application', subtype='pdf', filename=resume_file)

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(sender_email, app_pwd)
            smtp.send_message(msg)

# ----------------- MONTHLY ANALYTICS & LEARNING AGENT -----------------
class AnalyticsAgent:
    @staticmethod
    def generate_monthly_report():
        """Aggregates applications and missing skills to send monthly feedback report."""
        conn = sqlite3.connect("job_agent_system.db")
        cursor = conn.cursor()
        
        one_month_ago = datetime.now() - timedelta(days=30)
        cursor.execute("SELECT company_name, position, platform, match_score, applied_at FROM applications WHERE applied_at >= ?", (one_month_ago,))
        apps = cursor.fetchall()
        
        cursor.execute("SELECT missing_skills FROM skill_gap_logs WHERE recorded_at >= ?", (one_month_ago,))
        gaps = cursor.fetchall()
        conn.close()

        skill_frequency = {}
        for row in gaps:
            if row[0] and row[0] != "None":
                for skill in row[0].split(','):
                    s = skill.strip()
                    skill_frequency[s] = skill_frequency.get(s, 0) + 1

        # Synthesize report with Gemini
        analysis_prompt = f"""
        Analyze this month's job hunting statistics for Harsh Gupta:
        - Total Applications Sent: {len(apps)}
        - Frequently Missing Skills in Job Market: {skill_frequency}

        Produce an executive monthly intelligence report covering:
        1. Application Summary.
        2. Top 3 In-Demand Skills to Learn next to improve conversion rates.
        3. Strategic Action Plan for the upcoming month.
        """
        report_content = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=analysis_prompt
        ).text

        # Send report
        sender_email = os.getenv("SENDER_EMAIL")
        app_pwd = os.getenv("EMAIL_APP_PASSWORD")
        target_email = os.getenv("MONTHLY_REPORT_RECEIVER", "cryptomarketanalysis12@gmail.com")

        msg = EmailMessage()
        msg['Subject'] = f"Monthly Career Agent Intelligence Report - {datetime.now().strftime('%B %Y')}"
        msg['From'] = sender_email
        msg['To'] = target_email
        msg.set_content(report_content)

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(sender_email, app_pwd)
            smtp.send_message(msg)