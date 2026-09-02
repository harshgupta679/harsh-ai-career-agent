import os
import time
import re
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
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Absolute paths for resumes
RESUME_MAPPING = {
    "Data Analyst": os.path.abspath("Harsh_Gupta_Resume_DataAnalyst.pdf"),
    "Data Scientist": os.path.abspath("Harsh_Gupta_Resume_DataScientist.pdf")
}

# --- Pydantic Schema for Structured Evaluation ---
class EvaluationSchema(BaseModel):
    match_score: float = Field(description="ATS match score from 0 to 100")
    apply_verdict: bool = Field(description="True if fresher-eligible and match_score >= 65, else False")
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
        time.sleep(2)  # Rate-limit buffer
        
        # Pre-check for strict Senior / Experienced exclusions
        pos_lower = position.lower()
        desc_lower = description.lower()
        senior_terms = ["senior", "sr.", "lead", "principal", "manager", "director", "head", "staff", "vp", "architect"]
        
        if any(term in pos_lower for term in senior_terms):
            print(f"[MATCHER EXCLUSION] Skipping Senior/Lead role: {position}")
            return EvaluationSchema(
                match_score=0.0,
                apply_verdict=False,
                selected_role="Data Analyst",
                missing_skills=["Senior / Lead experience not matched"]
            )

        try:
            client = genai.Client(api_key=GEMINI_API_KEY)
            prompt = f"""
You are an expert Technical Recruiter evaluating candidate Harsh Gupta strictly for FRESHER / ENTRY-LEVEL job openings.

Candidate Profile:
- Experience Level: 0 Years (Fresh Graduate / College Student / Fresher / Intern)
- Skills: Data Analytics, Python, SQL, Machine Learning, PowerBI/Tableau, Generative AI & Automation.
- Target Roles: Data Analyst, Data Scientist, Junior / Entry-Level / Intern roles.

Target Position: {position}
Job Description: {description}

STRICT REJECTION RULES (MANDATORY):
1. If the job explicitly demands 1+ years, 2+ years, 3+ years or higher full-time industry experience, REJECT IT IMMEDIATELY (match_score = 0, apply_verdict = false).
2. If the role is for Senior, Lead, Manager, or Experienced professionals, REJECT IT IMMEDIATELY (apply_verdict = false).
3. ONLY approve (apply_verdict = true) if the position is open for Freshers, 0 Years Experience, Interns, College Graduates, Trainees, or Junior/Entry-Level candidates AND the technical ATS match is >= 65%.

Output JSON matching schema:
- match_score: 0 to 100
- apply_verdict: true if fresher-eligible AND score >= 65, else false
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

        except Exception as e:
            print(f"[GEMINI EVAL ADAPTIVE] Fallback scoring applied: {e}")
            
            # Algorithmic fallback with strict Fresher check
            exp_patterns = [r"\b[1-9]\d*\s*\+?\s*years?\b", r"\b[2-9]\s*to\s*\d+\s*years?\b"]
            has_high_exp = any(re.search(pat, desc_lower) for pat in exp_patterns)
            
            if has_high_exp and "intern" not in pos_lower and "fresher" not in desc_lower:
                return EvaluationSchema(
                    match_score=0.0,
                    apply_verdict=False,
                    selected_role="Data Analyst",
                    missing_skills=["Requires Prior Industry Experience"]
                )

            keywords = ["python", "sql", "analyst", "data", "tableau", "power bi", "machine learning", "ml"]
            matches = sum(1 for k in keywords if k in desc_lower or k in pos_lower)
            score = min(88.0, 50.0 + (matches * 6.0))
            is_ds = any(k in pos_lower or k in desc_lower for k in ["scientist", "machine learning", "ml", "ai"])
            
            return EvaluationSchema(
                match_score=score,
                apply_verdict=(score >= 65.0),
                selected_role="Data Scientist" if is_ds else "Data Analyst",
                missing_skills=["Advanced BI Tooling"] if score < 75 else []
            )


# --- 3. Cold Email & Application Agent ---
class ApplicationAgent:
    @staticmethod
    def generate_cold_email(company: str, position: str, job_description: str, role_type: str) -> dict:
        time.sleep(1.5)
        try:
            client = genai.Client(api_key=GEMINI_API_KEY)
            prompt = f"""
You are Harsh Gupta writing a direct, high-impact job application email to the Hiring Team at {company}.
Target Position: {position}
Domain: {role_type}

Job Description / Core Requirements:
{job_description}

Candidate Profile (Harsh Gupta):
- Expertise: Data Analytics, Python, SQL, Machine Learning, Tableau/PowerBI, LLMs/Agentic Workflows.
- Background: Motivated fresher with hands-on project experience in data analytics pipelines, dashboards, and machine learning models.
- Contact: harshgupta06504@gmail.com | LinkedIn: https://www.linkedin.com/in/harshgupta679

Email Writing Guidelines:
1. Subject Line: Clean corporate format (e.g., "Application for {position} - Harsh Gupta").
2. Tone: Confident, enthusiastic fresher, polite, concise (under 150 words).
3. Paragraph 1: Mention passion for the {position} role at {company}.
4. Paragraph 2: Highlight core skills (Python, SQL, {role_type} tools) and readiness to deliver immediate value.
5. Paragraph 3: Mention attached resume and express enthusiasm for a brief conversation.
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
        except Exception:
            return {
                "subject": f"Application for {position} - Harsh Gupta",
                "body": f"Hi Hiring Team,\n\nI am excited to submit my application for the {position} role at {company}. As a passionate fresher with strong practical skills in Python, SQL, data analysis, and {role_type} methodologies, I am eager to contribute to your data initiatives.\n\nPlease find my resume attached for your review. I would welcome the opportunity to discuss how my skill set aligns with your team's goals.\n\nBest regards,\nHarsh Gupta\nharshgupta06504@gmail.com"
            }

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