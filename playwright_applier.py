import os
import time
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv()

LINKEDIN_USER = os.getenv("LINKEDIN_USERNAME")
LINKEDIN_PASS = os.getenv("LINKEDIN_PASSWORD")

RESUME_MAPPING = {
    "Data Analyst": os.path.abspath("Harsh_Gupta_Resume_DataAnalyst.pdf"),
    "Data Scientist": os.path.abspath("Harsh_Gupta_Resume_DataScientist.pdf")
}

class LinkedInEasyApplyAgent:
    @staticmethod
    def get_resume_path(role_type: str) -> str:
        if "Scientist" in role_type or "Machine Learning" in role_type or "AI" in role_type:
            path = RESUME_MAPPING["Data Scientist"]
        else:
            path = RESUME_MAPPING["Data Analyst"]
        if os.path.exists(path):
            return path
        for file in os.listdir("."):
            if file.endswith(".pdf"):
                return os.path.abspath(file)
        return ""

    @staticmethod
    def fill_form_fields(page):
        """Intelligently handles screening questions, text boxes, and radios."""
        try:
            # 1. Fill empty text inputs (years of experience / numbers)
            text_inputs = page.locator("input[type='text'], input[type='number']")
            for i in range(text_inputs.count()):
                input_field = text_inputs.nth(i)
                if input_field.is_visible() and not input_field.input_value():
                    input_field.fill("2")  # Default safe experience estimate
                    page.wait_for_timeout(300)

            # 2. Select positive radio buttons (e.g. Work authorization -> Yes)
            yes_radios = page.locator("label:has-text('Yes'), label:has-text('Authorized')")
            for i in range(yes_radios.count()):
                radio = yes_radios.nth(i)
                if radio.is_visible():
                    try:
                        radio.click()
                    except Exception:
                        pass
        except Exception as e:
            print(f"[PLAYWRIGHT] Form auto-fill helper note: {e}")

    @staticmethod
    def apply_to_job(job_url: str, role_type: str = "Data Analyst") -> bool:
        if not LINKEDIN_USER or not LINKEDIN_PASS:
            print("[PLAYWRIGHT] LinkedIn credentials missing in .env")
            return False

        resume_path = LinkedInEasyApplyAgent.get_resume_path(role_type)
        if not resume_path:
            print("[PLAYWRIGHT ERROR] No resume file found!")
            return False

        with sync_playwright() as p:
            # Launch browser with realistic user-agent
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800}
            )
            page = context.new_page()

            try:
                # 1. Login
                page.goto("https://www.linkedin.com/login", timeout=30000)
                page.fill("#username", LINKEDIN_USER)
                page.fill("#password", LINKEDIN_PASS)
                page.click("button[type='submit']")
                page.wait_for_timeout(5000)

                # Check if security challenge triggered
                if "checkpoint" in page.url or "challenge" in page.url:
                    print("[PLAYWRIGHT SECURITY] LinkedIn CAPTCHA / Security checkpoint detected.")
                    browser.close()
                    return False

                # 2. Open Job
                print(f"[PLAYWRIGHT] Navigating to target job: {job_url}")
                page.goto(job_url, timeout=30000)
                page.wait_for_timeout(3000)

                # 3. Detect Easy Apply Button
                apply_button = page.locator("button.jobs-apply-button")
                if apply_button.count() == 0:
                    print("[PLAYWRIGHT] Job does not have direct LinkedIn Easy Apply.")
                    browser.close()
                    return False

                apply_button.first.click()
                page.wait_for_timeout(2000)

                # 4. Multi-Step Form Submission Loop (Max 8 steps)
                for _ in range(8):
                    # Upload Resume
                    file_input = page.locator("input[type='file']")
                    if file_input.count() > 0:
                        try:
                            file_input.first.set_input_files(resume_path)
                            page.wait_for_timeout(1000)
                        except Exception:
                            pass

                    # Answer Common Questions
                    LinkedInEasyApplyAgent.fill_form_fields(page)

                    # Check for Final Submit Button
                    submit_button = page.locator("button:has-text('Submit application')")
                    if submit_button.count() > 0 and submit_button.first.is_visible():
                        submit_button.first.click()
                        page.wait_for_timeout(3000)
                        print("[PLAYWRIGHT] Successfully Submitted Application!")
                        browser.close()
                        return True

                    # Click Next or Review
                    next_button = page.locator("button:has-text('Next'), button:has-text('Review')")
                    if next_button.count() > 0 and next_button.first.is_visible():
                        next_button.first.click()
                        page.wait_for_timeout(2000)
                    else:
                        break

                browser.close()
                return False

            except Exception as e:
                print(f"[PLAYWRIGHT EXCEPTION] {e}")
                browser.close()
                return False