import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from google import genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")

# Dynamic Resume Paths
RESUME_MAPPING = {
    "Data Analyst": os.path.abspath("Harsh_Gupta_Resume_DataAnalyst.pdf"),
    "Data Scientist": os.path.abspath("Harsh_Gupta_Resume_DataScientist.pdf")
}

class ApplicationAgent:
    @staticmethod
    def generate_cold_email(company: str, position: str, job_description: str, role_type: str) -> dict:
        """Uses Gemini to generate a tailored, professional cold outreach email."""
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        prompt = f"""
        You are an expert career agent writing a cold outreach job application email.
        
        Candidate Details:
        - Name: Harsh Gupta
        - Target Role: {position} at {company}
        - Domain: {role_type} (Data Analytics / Data Science / GenAI)
        - Contact Info: harshgupta06504@gmail.com | LinkedIn: linkedin.com/in/harshgupta679
        
        Job Context / Requirements:
        {job_description}
        
        Task:
        1. Write a compelling Subject line.
        2. Write a concise, high-impact 3-paragraph cold email showing genuine value, tailored to the job description.
        3. Mention that the resume is attached.
        4. Include the complete signature block with Harsh's contact details.
        
        Format your response EXACTLY as:
        SUBJECT: <Email Subject>
        BODY:
        <Email Body>
        """
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
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
        """Generates email draft, attaches resume, and sends via SMTP."""
        if not SENDER_EMAIL or not EMAIL_APP_PASSWORD or not recipient_email:
            print("[EMAIL AGENT] Missing email configuration or recipient.")
            return False

        # 1. Draft Email with Gemini
        draft = ApplicationAgent.generate_cold_email(company, position, job_description, role_type)
        
        # 2. Select Relevant Resume
        resume_path = RESUME_MAPPING.get("Data Scientist") if ("Scientist" in role_type or "AI" in role_type) else RESUME_MAPPING.get("Data Analyst")
        
        # 3. Create MIME Message
        msg = MIMEMultipart()
        msg["From"] = SENDER_EMAIL
        msg["To"] = recipient_email
        msg["Subject"] = draft["subject"]
        msg.attach(MIMEText(draft["body"], "plain"))

        # 4. Attach Resume PDF
        if resume_path and os.path.exists(resume_path):
            with open(resume_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename={os.path.basename(resume_path)}",
            )
            msg.attach(part)
            print(f"[EMAIL AGENT] Attached {os.path.basename(resume_path)}")

        # 5. Send via Gmail SMTP
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(SENDER_EMAIL, EMAIL_APP_PASSWORD)
                server.send_message(msg)
            print(f"[EMAIL SUCCESS] Cold email dispatched to {recipient_email}")
            return True
        except Exception as e:
            print(f"[EMAIL ERROR] Failed to send email: {e}")
            return False