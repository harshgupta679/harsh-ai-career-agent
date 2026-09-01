import re
import requests
from bs4 import BeautifulSoup
from agent_core import SecurityVerificationAgent

TARGET_ROLES = ["Data Analyst", "Data Scientist"]

def extract_recruiter_email(description: str) -> str:
    if not description:
        return ""
    emails = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', description)
    for email in emails:
        if SecurityVerificationAgent.validate_contact_email(email):
            return email.strip()
    return ""

def fetch_live_jobs() -> list:
    scouted_jobs = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }

    for role_keyword in TARGET_ROLES:
        print(f"[JOB SCOUT] Scanning 24/7 postings for: {role_keyword}...")
        encoded_role = role_keyword.replace(" ", "%20")
        url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={encoded_role}&location=India&start=0"
        
        try:
            response = requests.get(url, headers=headers, timeout=20)
            if response.status_code != 200:
                print(f"[JOB SCOUT] LinkedIn HTTP {response.status_code} for {role_keyword}")
                continue

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
                raw_link = link_tag.get("href", "")
                clean_link = raw_link.split("?")[0].strip()

                desc_text = f"Hiring for {position} at {company}. Requirements: Python, SQL, Data Analytics, Machine Learning, PowerBI, Tableau, Data Pipelines."
                recruiter_email = extract_recruiter_email(desc_text)

                scouted_jobs.append({
                    "company": company,
                    "position": position,
                    "apply_link": clean_link,
                    "description": desc_text,
                    "recruiter_email": recruiter_email
                })

        except Exception as e:
            print(f"[JOB SCOUT ERROR] {role_keyword}: {e}")

    return scouted_jobs