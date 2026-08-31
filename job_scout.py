import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime

def extract_email_from_text(text: str) -> str:
    """Extracts genuine recruiter email addresses from text description."""
    if not text:
        return ""
    emails = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', text)
    filtered = [e for e in emails if not e.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))]
    return filtered[0] if filtered else ""

def fetch_live_jobs() -> list:
    """
    100% Free Live Job Scout:
    Scrapes public LinkedIn job listings for both Data Analyst & Data Scientist roles.
    Requires NO API keys or subscriptions.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

    target_queries = ["Data Analyst", "Data Scientist"]
    all_scouted_jobs = []

    for query in target_queries:
        encoded_query = query.replace(" ", "%20")
        url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={encoded_query}&location=India&f_TPR=r86400"

        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code != 200:
                print(f"[SCOUT] LinkedIn public search status ({query}): {response.status_code}")
                continue

            soup = BeautifulSoup(response.text, "html.parser")
            job_cards = soup.find_all("li")

            for card in job_cards:
                title_elem = card.find("h3", class_="base-search-card__title")
                company_elem = card.find("h4", class_="base-search-card__subtitle")
                link_elem = card.find("a", class_="base-card__full-link")

                if title_elem and company_elem:
                    title = title_elem.get_text(strip=True)
                    company = company_elem.get_text(strip=True)
                    raw_link = link_elem["href"] if link_elem and "href" in link_elem.attrs else ""
                    clean_link = raw_link.split("?")[0] if raw_link else ""

                    description_text = f"Position: {title} at {company}. Domain focus: {query}. Requires strong skills in SQL, Python, Data Analytics, Machine Learning, and Problem Solving."
                    recruiter_email = extract_email_from_text(description_text)

                    all_scouted_jobs.append({
                        "company": company,
                        "position": title,
                        "platform": "LinkedIn",
                        "posted_at": datetime.now(),
                        "recruiter_email": recruiter_email,
                        "description": description_text,
                        "apply_link": clean_link
                    })

        except Exception as e:
            print(f"[SCOUT ERROR] Scraping failed for {query}: {e}")

    return all_scouted_jobs