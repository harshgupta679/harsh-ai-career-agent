import sqlite3
from datetime import datetime, timedelta

DB_NAME = "career_agent.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Table enforcing No-Spam duplicate prevention
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            position TEXT NOT NULL,
            platform TEXT NOT NULL,
            contact_email TEXT,
            applied_resume_role TEXT NOT NULL,
            match_score REAL NOT NULL,
            applied_at TIMESTAMP NOT NULL,
            status TEXT NOT NULL,
            UNIQUE(company_name, position)
        )
    ''')
    
    # Table recording skill gaps for skipped or low-score jobs
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

def is_already_applied(company: str, position: str) -> bool:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM applications WHERE LOWER(company_name) = LOWER(?) AND LOWER(position) = LOWER(?)", (company, position))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

def log_application(company: str, position: str, platform: str, email: str, role: str, score: float):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO applications (company_name, position, platform, contact_email, applied_resume_role, match_score, applied_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (company, position, platform, email, role, score, datetime.now(), "Applied"))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def log_skill_gap(job_title: str, company: str, missing_skills: list):
    if not missing_skills:
        return
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO skill_gap_logs (job_title, company, missing_skills, recorded_at)
        VALUES (?, ?, ?, ?)
    ''', (job_title, company, ", ".join(missing_skills), datetime.now()))
    conn.commit()
    conn.close()