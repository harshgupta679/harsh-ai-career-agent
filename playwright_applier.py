import os
import time
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv()

LINKEDIN_USER = os.getenv("LINKEDIN_USERNAME")
LINKEDIN_PASS = os.getenv("LINKEDIN_PASSWORD")
RESUME_PATH = os.path.abspath("resume.pdf")

class LinkedInEasyApplyAgent:
    @staticmethod
    def apply_to_job(job_url: str, role_type: str = "General") -> bool:
        if not LINKEDIN_USER or not LINKEDIN_PASS:
            print("[PLAYWRIGHT] LinkedIn credentials missing in .env")
            return False

        if not os.path.exists(RESUME_PATH):
            print(f"[PLAYWRIGHT ERROR] {RESUME_PATH} file nahi mili! Folder mein resume.pdf rakhein.")
            return False

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 800})
            page = context.new_page()

            try:
                # 1. Login to LinkedIn
                page.goto("https://www.linkedin.com/login", timeout=30000)
                page.fill("#username", LINKEDIN_USER)
                page.fill("#password", LINKEDIN_PASS)
                page.click("button[type='submit']")
                page.wait_for_timeout(4000)

                # 2. Open Job Page
                print(f"[PLAYWRIGHT] Navigating to: {job_url}")
                page.goto(job_url, timeout=30000)
                page.wait_for_timeout(3000)

                # 3. Check for Easy Apply Button
                easy_apply_btn = page.locator("button.jobs-apply-button")
                if easy_apply_btn.count() == 0:
                    print("[PLAYWRIGHT] Easy Apply button not found (Direct company site link).")
                    browser.close()
                    return False

                easy_apply_btn.first.click()
                page.wait_for_timeout(2000)

                # 4. Multi-Step Form Fill & Resume Upload Loop
                for step in range(5):
                    # Check for Resume File Upload Input
                    file_input = page.locator("input[type='file']")
                    if file_input.count() > 0:
                        try:
                            file_input.first.set_input_files(RESUME_PATH)
                            print(f"[PLAYWRIGHT] Uploaded {RESUME_PATH} successfully.")
                            page.wait_for_timeout(1500)
                        except Exception as e:
                            print(f"[PLAYWRIGHT] Resume upload skip/error: {e}")

                    # Check for Submit / Next / Review Buttons
                    submit_btn = page.locator("button:has-text('Submit application')")
                    if submit_btn.count() > 0 and submit_btn.first.is_visible():
                        submit_btn.first.click()
                        page.wait_for_timeout(3000)
                        print("[PLAYWRIGHT] Application Submitted Successfully!")
                        browser.close()
                        return True

                    next_btn = page.locator("button:has-text('Next'), button:has-text('Review')")
                    if next_btn.count() > 0 and next_btn.first.is_visible():
                        next_btn.first.click()
                        page.wait_for_timeout(2000)
                    else:
                        break

                browser.close()
                return False

            except Exception as e:
                print(f"[PLAYWRIGHT ERROR] {e}")
                browser.close()
                return False