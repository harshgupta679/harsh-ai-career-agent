import sqlite3
import os
from datetime import datetime
from typing import List, Union

DB_NAME = os.path.abspath("career_agent.db")

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. Applications Table (URL / Role unique to allow new company openings)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            position TEXT NOT NULL,
            platform TEXT NOT NULL,
            contact_email TEXT,
            applied_resume_role TEXT NOT NULL,
            match_score REAL NOT NULL,
            status TEXT NOT NULL,
            job_url TEXT UNIQUE,
            applied_at TIMESTAMP NOT NULL
        )
    ''')
    
    # 2. Skill Gap Logs Table (Records missing skills for rejected/low-match jobs)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS skill_gap_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_title TEXT NOT NULL,
            company TEXT NOT NULL,
            missing_skills TEXT NOT NULL,
            recorded_at TIMESTAMP NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def is_already_applied(company: str, position: str, job_url: str = "") -> bool:
    """Checks strictly by unique URL first, then falls back to Company + Position match."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    if job_url:
        clean_url = job_url.split("?")[0].strip()
        cursor.execute("SELECT 1 FROM applications WHERE job_url = ?", (clean_url,))
        exists = cursor.fetchone() is not None
        if exists:
            conn.close()
            return True

    cursor.execute(
        "SELECT 1 FROM applications WHERE LOWER(company_name) = LOWER(?) AND LOWER(position) = LOWER(?)", 
        (company.strip(), position.strip())
    )
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

# Backward compatibility alias
is_job_applied = is_already_applied

def log_application(
    company: str, 
    position: str, 
    platform: str, 
    score: float, 
    status: str = "Applied", 
    job_url: str = "", 
    email: str = "", 
    role: str = "Data Analyst"
) -> bool:
    clean_url = job_url.split("?")[0].strip() if job_url else f"{company}_{position}_{datetime.now().isoformat()}"
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO applications (
                company_name, position, platform, contact_email, 
                applied_resume_role, match_score, status, job_url, applied_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (company.strip(), position.strip(), platform, email, role, score, status, clean_url, datetime.now()))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def log_skill_gap(job_title: str, company: str, missing_skills: Union[List[str], str]):
    if not missing_skills:
        return
    
    if isinstance(missing_skills, list):
        skills_str = ", ".join(missing_skills)
    else:
        skills_str = str(missing_skills)

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO skill_gap_logs (job_title, company, missing_skills, recorded_at)
        VALUES (?, ?, ?, ?)
    ''', (job_title.strip(), company.strip(), skills_str, datetime.now()))
    conn.commit()
    conn.close()

def get_monthly_stats() -> dict:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM applications")
    total_apps = cursor.fetchone()[0]
    
    cursor.execute("SELECT missing_skills FROM skill_gap_logs ORDER BY recorded_at DESC LIMIT 50")
    gaps = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    return {
        "total_tracked_applications": total_apps,
        "recent_skill_gaps": gaps
    }

# Initialize database schema immediately on import
init_db()