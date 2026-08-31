import os
import time
import random
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

load_dotenv()

USER_DATA_DIR = "./playwright_user_data"
RESUME_MAP = {
    "Data Analyst": str(Path("Harsh_Gupta_Resume_DataAnalyst.pdf").resolve()),
    "Data Scientist": str(Path("Harsh_Gupta_Resume_DataScientist.pdf").resolve())
}

CANDIDATE_PHONE = "7906936146"

def human_delay(min_sec=1.5, max_sec=3.5):
    """Randomized sleep to emulate human interaction and avoid bot triggers."""
    time.sleep(random.uniform(min_sec, max_sec))

class LinkedInEasyApplyAgent:
    @staticmethod
    def apply_to_job(job_url: str, selected_role: str) -> bool:
        """
        Launches Playwright, logs in (or reuses active session),
        fills the Easy Apply modal, attaches resume, and submits.
        """
        resume_path = RESUME_MAP.get(selected_role)
        if not resume_path or not os.path.exists(resume_path):
            print(f"[PLAYWRIGHT] Error: Resume file for '{selected_role}' not found.")
            return False

        with sync_playwright() as p:
            # Launch persistent browser context to retain login session
            context = p.chromium.launch_persistent_context(
                user_data_dir=USER_DATA_DIR,
                headless=False,  # Set to False to monitor interaction or complete manual CAPTCHA/2FA once
                args=["--disable-blink-features=AutomationControlled", "--start-maximized"]
            )
            page = context.new_page()

            try:
                # 1. Check Authentication Status
                page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
                human_delay(2, 3)

                if "login" in page.url or "checkpoint" in page.url:
                    print("[PLAYWRIGHT] Logging into LinkedIn...")
                    page.goto("https://www.linkedin.com/login")
                    page.fill("#username", os.getenv("LINKEDIN_USERNAME"))
                    human_delay(1, 2)
                    page.fill("#password", os.getenv("LINKEDIN_PASSWORD"))
                    human_delay(1, 2)
                    page.click("button[type='submit']")
                    page.wait_for_load_state("networkidle")
                    human_delay(3, 5)

                # 2. Navigate directly to Job URL
                print(f"[PLAYWRIGHT] Navigating to: {job_url}")
                page.goto(job_url, wait_until="domcontentloaded")
                human_delay(2, 4)

                # 3. Locate Easy Apply Button
                easy_apply_btn = page.locator("button.jobs-apply-button:has-text('Easy Apply')").first
                if not easy_apply_btn.is_visible():
                    print("[PLAYWRIGHT] No standard 'Easy Apply' button found on page.")
                    context.close()
                    return False

                easy_apply_btn.click()
                human_delay(1.5, 2.5)

                # 4. Step-through Multi-Step Modal Form
                max_steps = 6
                for step in range(max_steps):
                    # Fill phone number if input field is empty
                    phone_input = page.locator("input[id*='phoneNumber']").first
                    if phone_input.is_visible() and not phone_input.input_value():
                        phone_input.fill(CANDIDATE_PHONE)

                    # Handle File/Resume Upload input
                    upload_input = page.locator("input[type='file']").first
                    if upload_input.is_visible():
                        try:
                            upload_input.set_input_files(resume_path)
                            human_delay(1.5, 2.5)
                        except Exception as e:
                            print(f"[PLAYWRIGHT] Resume upload fallback: {e}")

                    # Submit button check (final step)
                    submit_btn = page.locator("button:has-text('Submit application')").first
                    if submit_btn.is_visible():
                        human_delay(1, 2)
                        submit_btn.click()
                        print(f"[PLAYWRIGHT] Successfully submitted application for {selected_role}!")
                        human_delay(3, 4)
                        context.close()
                        return True

                    # Review button check
                    review_btn = page.locator("button:has-text('Review')").first
                    if review_btn.is_visible():
                        review_btn.click()
                        human_delay(1.5, 2.5)
                        continue

                    # Next button check
                    next_btn = page.locator("button:has-text('Next')").first
                    if next_btn.is_visible():
                        next_btn.click()
                        human_delay(1.5, 2.5)
                        continue

                    # If no valid progression buttons are found
                    print("[PLAYWRIGHT] Complex custom question or unhandled form step encountered. Aborting.")
                    break

                context.close()
                return False

            except Exception as e:
                print(f"[PLAYWRIGHT ERROR] {e}")
                context.close()
                return False