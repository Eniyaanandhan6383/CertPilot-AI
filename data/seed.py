"""
CertPilot AI — Synthetic Data Seeder
Generates all base data for demo. Run once: python -m data.seed
"""

import sqlite3
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "certpilot.db"


# ── Schema ─────────────────────────────────────────────────────────────────

SCHEMA = """
CREATE TABLE IF NOT EXISTS employees (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    role            TEXT NOT NULL,
    department      TEXT NOT NULL,
    manager_id      INTEGER,
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS certifications (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    code            TEXT UNIQUE NOT NULL,
    name            TEXT NOT NULL,
    level           TEXT NOT NULL,          -- Fundamentals | Associate | Expert
    passing_score   INTEGER NOT NULL,       -- percentage
    exam_duration_hours REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS employee_certifications (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id         INTEGER NOT NULL,
    certification_id    INTEGER NOT NULL,
    status              TEXT NOT NULL,      -- enrolled | in_progress | passed | failed
    target_exam_date    TEXT,
    attempt_count       INTEGER DEFAULT 0,
    last_score          INTEGER,
    enrolled_at         TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (employee_id) REFERENCES employees(id),
    FOREIGN KEY (certification_id) REFERENCES certifications(id)
);

CREATE TABLE IF NOT EXISTS learning_activities (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id         INTEGER NOT NULL,
    certification_id    INTEGER NOT NULL,
    activity_type       TEXT NOT NULL,      -- module | quiz | lab | practice_exam
    topic               TEXT NOT NULL,
    duration_minutes    INTEGER,
    score               INTEGER,            -- 0-100, NULL for modules
    completed_at        TEXT NOT NULL,
    FOREIGN KEY (employee_id) REFERENCES employees(id),
    FOREIGN KEY (certification_id) REFERENCES certifications(id)
);

CREATE TABLE IF NOT EXISTS study_plans (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id         INTEGER NOT NULL,
    certification_id    INTEGER NOT NULL,
    daily_hours         REAL,
    start_date          TEXT,
    target_date         TEXT,
    plan_data_json      TEXT,               -- full agent-generated plan
    created_at          TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (employee_id) REFERENCES employees(id),
    FOREIGN KEY (certification_id) REFERENCES certifications(id)
);

CREATE TABLE IF NOT EXISTS risk_assessments (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id         INTEGER NOT NULL,
    certification_id    INTEGER NOT NULL,
    risk_level          TEXT NOT NULL,      -- LOW | MEDIUM | HIGH
    risk_score          INTEGER NOT NULL,   -- 0-100
    risk_reasons        TEXT NOT NULL,      -- JSON array of reason strings
    weak_topics         TEXT NOT NULL,      -- JSON array of topic strings
    assessed_at         TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (employee_id) REFERENCES employees(id),
    FOREIGN KEY (certification_id) REFERENCES certifications(id)
);

CREATE TABLE IF NOT EXISTS interventions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id         INTEGER NOT NULL,
    certification_id    INTEGER NOT NULL,
    risk_assessment_id  INTEGER NOT NULL,
    recommendations     TEXT NOT NULL,      -- JSON array
    priority            TEXT NOT NULL,      -- IMMEDIATE | SOON | OPTIONAL
    created_at          TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (employee_id) REFERENCES employees(id),
    FOREIGN KEY (risk_assessment_id) REFERENCES risk_assessments(id)
);
"""


# ── Seed Data ───────────────────────────────────────────────────────────────

CERTIFICATIONS = [
    {"code": "AZ-900", "name": "Microsoft Azure Fundamentals",
     "level": "Fundamentals", "passing_score": 700, "exam_duration_hours": 1.0},
    {"code": "AZ-104", "name": "Microsoft Azure Administrator",
     "level": "Associate",    "passing_score": 700, "exam_duration_hours": 2.0},
    {"code": "AZ-305", "name": "Microsoft Azure Solutions Architect Expert",
     "level": "Expert",       "passing_score": 700, "exam_duration_hours": 2.5},
]

# 2 managers first (manager_id = NULL), then 8 employees
EMPLOYEES = [
    # Managers
    {"name": "Kavya Reddy",     "role": "Engineering Manager",  "department": "Engineering",  "manager_id": None},
    {"name": "Suresh Babu",     "role": "IT Director",          "department": "Operations",   "manager_id": None},
    # Engineering team (manager_id = 1)
    {"name": "Arjun Mehta",     "role": "Cloud Engineer",       "department": "Engineering",  "manager_id": 1},
    {"name": "Priya Nair",      "role": "DevOps Lead",          "department": "Engineering",  "manager_id": 1},
    {"name": "Sneha Iyer",      "role": "Solutions Architect",  "department": "Engineering",  "manager_id": 1},
    {"name": "Karthik Rajan",   "role": "Cloud Architect",      "department": "Engineering",  "manager_id": 1},
    {"name": "Arun Kumar",      "role": "DevOps Engineer",      "department": "Engineering",  "manager_id": 1},
    {"name": "Vikram Das",      "role": "Junior Engineer",      "department": "Engineering",  "manager_id": 1},
    # Operations team (manager_id = 2)
    {"name": "Rahul Sharma",    "role": "IT Administrator",     "department": "Operations",   "manager_id": 2},
    {"name": "Meera Pillai",    "role": "IT Manager",           "department": "Operations",   "manager_id": 2},
]

# employee index (0-based) → cert code, exam days from now, risk profile
ENROLLMENTS = [
    # eng manager
    {"emp_idx": 0, "cert": "AZ-305", "days_to_exam": 45,  "risk": "LOW"},
    # ops manager
    {"emp_idx": 1, "cert": "AZ-104", "days_to_exam": 30,  "risk": "MEDIUM"},
    # engineering team
    {"emp_idx": 2, "cert": "AZ-104", "days_to_exam": 30,  "risk": "LOW"},     # Arjun — consistent
    {"emp_idx": 3, "cert": "AZ-305", "days_to_exam": 21,  "risk": "HIGH"},    # Priya — weak networking
    {"emp_idx": 4, "cert": "AZ-305", "days_to_exam": 40,  "risk": "LOW"},     # Sneha — strong
    {"emp_idx": 5, "cert": "AZ-305", "days_to_exam": 35,  "risk": "MEDIUM"},  # Karthik — weak identity
    {"emp_idx": 6, "cert": "AZ-104", "days_to_exam": 28,  "risk": "MEDIUM"},  # Arun — inconsistent
    {"emp_idx": 7, "cert": "AZ-900", "days_to_exam": 20,  "risk": "LOW"},     # Vikram — easy cert
    # operations team
    {"emp_idx": 8, "cert": "AZ-104", "days_to_exam": 25,  "risk": "MEDIUM"},  # Rahul — weak hands-on
    {"emp_idx": 9, "cert": "AZ-104", "days_to_exam": 18,  "risk": "HIGH"},    # Meera — low study hours
]

# Topics per certification
CERT_TOPICS = {
    "AZ-900": ["Cloud Concepts", "Azure Services", "Security", "Pricing", "Governance"],
    "AZ-104": ["Identity & Access", "Virtual Networking", "Storage", "Compute", "Monitoring", "Backup"],
    "AZ-305": ["Identity Solutions", "Networking", "Storage Solutions", "Business Continuity",
                "Infrastructure", "Data Integration", "App Architecture", "Security"],
}

# Risk profile → score ranges per activity type
SCORE_PROFILES = {
    "LOW":    {"quiz": (72, 92), "practice_exam": (68, 88), "lab": (80, 100)},
    "MEDIUM": {"quiz": (52, 75), "practice_exam": (48, 68), "lab": (55, 80)},
    "HIGH":   {"quiz": (30, 58), "practice_exam": (28, 52), "lab": (20, 55)},
}

# HIGH risk employees have weak specific topics
WEAK_TOPIC_MAP = {
    3: ["Networking", "Business Continuity"],          # Priya
    9: ["Virtual Networking", "Identity & Access"],    # Meera
    1: ["Networking", "Monitoring"],                   # Suresh (ops manager, medium)
}


def rand_score(low, high):
    return random.randint(low, high)


def make_activities(emp_db_id: int, cert_db_id: int, cert_code: str,
                    risk: str, emp_idx: int, days_back: int = 35):
    """Generate 35 days of realistic learning history."""
    activities = []
    topics = CERT_TOPICS[cert_code]
    profile = SCORE_PROFILES[risk]
    weak_topics = WEAK_TOPIC_MAP.get(emp_idx, [])

    # HIGH risk = gaps in activity (5-day inactivity windows)
    skip_days = set()
    if risk == "HIGH":
        gap_start = random.randint(8, 20)
        skip_days = set(range(gap_start, gap_start + 5))
    elif risk == "MEDIUM":
        gap_start = random.randint(15, 25)
        skip_days = set(range(gap_start, gap_start + 2))

    for day in range(days_back, 0, -1):
        if day in skip_days:
            continue

        dt = (datetime.now() - timedelta(days=day)).strftime("%Y-%m-%d %H:%M:%S")
        topic = random.choice(topics)

        # Module completion (always)
        activities.append({
            "employee_id": emp_db_id,
            "certification_id": cert_db_id,
            "activity_type": "module",
            "topic": topic,
            "duration_minutes": random.randint(20, 60),
            "score": None,
            "completed_at": dt,
        })

        # Quiz every 2-3 days
        if day % 2 == 0:
            lo, hi = profile["quiz"]
            # weaken score on weak topics
            if any(wt.lower() in topic.lower() for wt in weak_topics):
                lo, hi = max(20, lo - 20), max(35, hi - 20)
            activities.append({
                "employee_id": emp_db_id,
                "certification_id": cert_db_id,
                "activity_type": "quiz",
                "topic": topic,
                "duration_minutes": random.randint(10, 20),
                "score": rand_score(lo, hi),
                "completed_at": dt,
            })

        # Lab every 4-5 days (HIGH risk skips more)
        if day % 5 == 0:
            if risk == "HIGH" and random.random() < 0.5:
                pass  # missed lab
            else:
                lo, hi = profile["lab"]
                activities.append({
                    "employee_id": emp_db_id,
                    "certification_id": cert_db_id,
                    "activity_type": "lab",
                    "topic": topic,
                    "duration_minutes": random.randint(30, 90),
                    "score": rand_score(lo, hi),
                    "completed_at": dt,
                })

        # Practice exam weekly
        if day % 7 == 0:
            lo, hi = profile["practice_exam"]
            activities.append({
                "employee_id": emp_db_id,
                "certification_id": cert_db_id,
                "activity_type": "practice_exam",
                "topic": "Full Exam",
                "duration_minutes": random.randint(60, 120),
                "score": rand_score(lo, hi),
                "completed_at": dt,
            })

    return activities


def seed():
    random.seed(42)  # reproducible demo data

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Drop and recreate
    cur.executescript("DROP TABLE IF EXISTS interventions;"
                      "DROP TABLE IF EXISTS risk_assessments;"
                      "DROP TABLE IF EXISTS study_plans;"
                      "DROP TABLE IF EXISTS learning_activities;"
                      "DROP TABLE IF EXISTS employee_certifications;"
                      "DROP TABLE IF EXISTS employees;"
                      "DROP TABLE IF EXISTS certifications;")
    cur.executescript(SCHEMA)

    # Certifications
    cert_id_map = {}
    for c in CERTIFICATIONS:
        cur.execute(
            "INSERT INTO certifications (code, name, level, passing_score, exam_duration_hours) "
            "VALUES (?, ?, ?, ?, ?)",
            (c["code"], c["name"], c["level"], c["passing_score"], c["exam_duration_hours"])
        )
        cert_id_map[c["code"]] = cur.lastrowid

    # Employees
    emp_db_ids = []
    for e in EMPLOYEES:
        cur.execute(
            "INSERT INTO employees (name, role, department, manager_id) VALUES (?, ?, ?, ?)",
            (e["name"], e["role"], e["department"], e["manager_id"])
        )
        emp_db_ids.append(cur.lastrowid)

    # Enrollments + activities
    for enr in ENROLLMENTS:
        idx = enr["emp_idx"]
        emp_db_id = emp_db_ids[idx]
        cert_code = enr["cert"]
        cert_db_id = cert_id_map[cert_code]
        exam_date = (datetime.now() + timedelta(days=enr["days_to_exam"])).strftime("%Y-%m-%d")

        cur.execute(
            "INSERT INTO employee_certifications "
            "(employee_id, certification_id, status, target_exam_date, attempt_count) "
            "VALUES (?, ?, 'in_progress', ?, 0)",
            (emp_db_id, cert_db_id, exam_date)
        )

        activities = make_activities(emp_db_id, cert_db_id, cert_code,
                                     enr["risk"], idx)
        cur.executemany(
            "INSERT INTO learning_activities "
            "(employee_id, certification_id, activity_type, topic, duration_minutes, score, completed_at) "
            "VALUES (:employee_id, :certification_id, :activity_type, :topic, "
            ":duration_minutes, :score, :completed_at)",
            activities
        )

    conn.commit()
    conn.close()

    # Summary
    conn2 = sqlite3.connect(DB_PATH)
    cur2 = conn2.cursor()
    print("✅ CertPilot database seeded successfully")
    print(f"   Employees:          {cur2.execute('SELECT COUNT(*) FROM employees').fetchone()[0]}")
    print(f"   Certifications:     {cur2.execute('SELECT COUNT(*) FROM certifications').fetchone()[0]}")
    print(f"   Enrollments:        {cur2.execute('SELECT COUNT(*) FROM employee_certifications').fetchone()[0]}")
    print(f"   Learning activities:{cur2.execute('SELECT COUNT(*) FROM learning_activities').fetchone()[0]}")
    conn2.close()
    print(f"\n   DB path: {DB_PATH}")


if __name__ == "__main__":
    seed()
