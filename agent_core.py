import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pydantic import BaseModel, Field
from google import genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

# Absolute paths for resumes
RESUME_MAPPING = {
    "Data Analyst": os.path.abspath("Harsh_Gupta_Resume_DataAnalyst.pdf"),
    "Data Scientist": os.path.abspath("Harsh_Gupta_Resume_DataScientist.pdf")
}

# --- Pydantic Schema for Structured Evaluation ---
class EvaluationSchema(BaseModel):
    match_score: float = Field(description="ATS match score from 0 to 100")
    apply_verdict: bool = Field(description="True if score >= 65, else False")
    selected_role: str = Field(description="'Data Analyst' or 'Data Scientist'")
    missing_skills: list[str] = Field(description="List of skills the candidate lacks")


# --- 1. Security Verification Agent ---
class SecurityVerificationAgent:
    @staticmethod
    def validate_contact_email(email: str) -> bool:
        if not email or "@" not in email:
            return False
        disallowed = ["no-reply", "noreply", "donotreply", "example.com", "test.com"]
        return not any(d in email.lower() for d in disallowed)


# --- 2. Matchmaker & ATS Evaluation Agent ---
class MatchmakerAgent:
    @staticmethod
    def evaluate_job(position: str, description: str) -> EvaluationSchema:
        client = genai.Client(api_key=GEMINI_API_KEY)
        prompt = f"""
Evaluate candidate Harsh Gupta against this job opening.

Candidate Profile:
- Strong hands-on background in Data Analytics, Python, SQL, Machine Learning, PowerBI/Tableau, and AI Agents.
- Resumes Available: Data Analyst & Data Scientist.

Target Role: {position}
Job Description: {description}

Analyze match and return JSON strictly matching schema:
- match_score: 0 to 100
- apply_verdict: true if match_score >= 65 else false
- selected_role: 'Data Analyst' or 'Data Scientist'
- missing_skills: list of missing tools/skills
"""
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": EvaluationSchema,
            }
        )
        return EvaluationSchema.model_validate_json(response.text)


# --- 3. Cold Email & Application Agent ---
class ApplicationAgent:
    @staticmethod
    def generate_cold_email(company: str, position: str, job_description: str, role_type: str) -> dict:
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        prompt = f"""
You are Harsh Gupta writing a direct, high-impact job application email to the Hiring Team at {company}.
Target Position: {position}
Domain: {role_type}

Job Description / Core Requirements:
{job_description}

Candidate Profile (Harsh Gupta):
- Expertise: Data Analytics, Python, SQL, Machine Learning, Tableau/PowerBI, LLMs/Agentic Workflows.
- Value Proposition: Strong foundation in building production-ready data pipelines, actionable dashboards, and applied AI automation.
- Contact: harshgupta06504@gmail.com | LinkedIn: https://www.linkedin.com/in/harshgupta679

Email Writing Guidelines:
1. Subject Line: Must be clean and corporate (e.g., "Application for {position} - Harsh Gupta").
2. Tone: Confident, polite, concise (under 160 words). No robotic/overly formal cliches.
3. Paragraph 1: State interest in the specific {position} role at {company} and alignment with their core stack.
4. Paragraph 2: Mention 2-3 specific technical capabilities directly addressing requirements.
5. Paragraph 3: Mention attached resume and suggest a brief connect.
6. Signature: Corporate clean format.

Output STRICTLY in this format:
SUBJECT: <Your Subject Line>
BODY:
<Your Full Email Body>
"""
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )
        text = response.text.strip()
        
        subject = f"Application for {position} - Harsh Gupta"
        body = text
        if "SUBJECT:" in text and "BODY:" in text:
            parts = text.split("BODY:")
            subject = parts[0].replace("SUBJECT:", "").strip()
            body = parts[1].strip()
            
        return {"subject": subject, "body": body}

    @staticmethod
    def dispatch_email_application(company: str, position: str, recipient_email: str, job_description: str = "", role_type: str = "Data Analyst") -> bool:
        if not SENDER_EMAIL or not EMAIL_APP_PASSWORD or not recipient_email:
            print("[EMAIL AGENT] Missing email credentials or recipient address.")
            return False

        draft = ApplicationAgent.generate_cold_email(company, position, job_description, role_type)
        
        is_ds_role = any(x in role_type.lower() for x in ["scientist", "machine learning", "ai", "ml"])
        resume_path = RESUME_MAPPING["Data Scientist"] if is_ds_role else RESUME_MAPPING["Data Analyst"]

        msg = MIMEMultipart()
        msg["From"] = f"Harsh Gupta <{SENDER_EMAIL}>"
        msg["To"] = recipient_email
        msg["Subject"] = draft["subject"]
        msg.attach(MIMEText(draft["body"], "plain"))

        if os.path.exists(resume_path):
            with open(resume_path, "rb") as f:
                attachment = MIMEBase("application", "pdf")
                attachment.set_payload(f.read())
            encoders.encode_base64(attachment)
            attachment.add_header(
                "Content-Disposition",
                f'attachment; filename="{os.path.basename(resume_path)}"'
            )
            msg.attach(attachment)
            print(f"[EMAIL AGENT] Attached Resume: {os.path.basename(resume_path)}")
        else:
            print(f"[EMAIL AGENT WARNING] Resume file not found at: {resume_path}")

        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(SENDER_EMAIL, EMAIL_APP_PASSWORD)
                server.send_message(msg)
            print(f"[EMAIL SUCCESS] Application dispatched to: {recipient_email}")
            return True
        except Exception as e:
            print(f"[EMAIL SMTP ERROR] {e}")
            return False


# --- 4. Analytics Agent ---
class AnalyticsAgent:
    @staticmethod
    def generate_and_send_monthly_report():
        print("[ANALYTICS AGENT] Monthly reporting cycle evaluated.")