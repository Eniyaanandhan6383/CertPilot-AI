"""
CertPilot AI — Deterministic Risk Scorer
Computes measurable signals from learning_activities before sending to LLM.
This grounds the LLM risk reasoning in real numbers.
"""
from __future__ import annotations
import sqlite3
from datetime import datetime, timedelta
from database import get_db


def compute_risk_signals(employee_id: int, certification_id: int) -> dict:
    """
    Returns a structured signal dict that gets injected into the Risk Agent prompt.
    All numbers are computed from actual learning_activities rows.
    """
    db = get_db()

    # ── 1. Average quiz scores per topic ───────────────────────────────────
    topic_scores = db.execute("""
        SELECT topic, AVG(score) as avg_score, COUNT(*) as attempts
        FROM learning_activities
        WHERE employee_id = ?
          AND certification_id = ?
          AND activity_type = 'quiz'
          AND score IS NOT NULL
        GROUP BY topic
        ORDER BY avg_score ASC
    """, (employee_id, certification_id)).fetchall()

    topic_score_map = {
        row["topic"]: {"avg_score": round(row["avg_score"], 1), "attempts": row["attempts"]}
        for row in topic_scores
    }

    weak_topics = [
        row["topic"] for row in topic_scores
        if row["avg_score"] is not None and row["avg_score"] < 60
    ]

    # ── 2. Lab completion rate ──────────────────────────────────────────────
    # Count days where a lab was expected (every 5 days) vs completed
    total_possible_labs = db.execute("""
        SELECT COUNT(DISTINCT date(completed_at)) as active_days
        FROM learning_activities
        WHERE employee_id = ? AND certification_id = ?
    """, (employee_id, certification_id)).fetchone()["active_days"]

    labs_completed = db.execute("""
        SELECT COUNT(*) as cnt
        FROM learning_activities
        WHERE employee_id = ?
          AND certification_id = ?
          AND activity_type = 'lab'
    """, (employee_id, certification_id)).fetchone()["cnt"]

    expected_labs = max(1, total_possible_labs // 5)
    lab_completion_rate = round(min(100, (labs_completed / expected_labs) * 100), 1)

    # ── 3. Study consistency — days since last activity ─────────────────────
    last_activity = db.execute("""
        SELECT MAX(completed_at) as last_dt
        FROM learning_activities
        WHERE employee_id = ? AND certification_id = ?
    """, (employee_id, certification_id)).fetchone()["last_dt"]

    days_inactive = 0
    if last_activity:
        last_dt = datetime.fromisoformat(last_activity)
        days_inactive = (datetime.now() - last_dt).days

    # ── 4. Recent practice exam scores (last 3) ─────────────────────────────
    recent_exams = db.execute("""
        SELECT score FROM learning_activities
        WHERE employee_id = ?
          AND certification_id = ?
          AND activity_type = 'practice_exam'
          AND score IS NOT NULL
        ORDER BY completed_at DESC
        LIMIT 3
    """, (employee_id, certification_id)).fetchall()
    recent_exam_scores = [r["score"] for r in recent_exams]
    avg_exam_score = round(sum(recent_exam_scores) / len(recent_exam_scores), 1) if recent_exam_scores else 0

    # ── 5. Study hours (last 14 days) ───────────────────────────────────────
    two_weeks_ago = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")
    study_minutes = db.execute("""
        SELECT COALESCE(SUM(duration_minutes), 0) as total
        FROM learning_activities
        WHERE employee_id = ?
          AND certification_id = ?
          AND completed_at >= ?
    """, (employee_id, certification_id, two_weeks_ago)).fetchone()["total"]
    study_hours_last_14d = round(study_minutes / 60, 1)

    # ── 6. Days to exam ─────────────────────────────────────────────────────
    enrollment = db.execute("""
        SELECT target_exam_date FROM employee_certifications
        WHERE employee_id = ? AND certification_id = ?
    """, (employee_id, certification_id)).fetchone()

    days_to_exam = None
    if enrollment and enrollment["target_exam_date"]:
        exam_dt = datetime.strptime(enrollment["target_exam_date"], "%Y-%m-%d")
        days_to_exam = (exam_dt - datetime.now()).days

    db.close()

    # ── Deterministic risk pre-score (0-100, higher = more risk) ───────────
    pre_score = 0
    flags = []

    if weak_topics:
        pre_score += min(40, len(weak_topics) * 12)
        flags.append(f"{len(weak_topics)} weak topic(s): {', '.join(weak_topics[:3])}")

    if lab_completion_rate < 60:
        pre_score += 20
        flags.append(f"Low lab completion: {lab_completion_rate}%")

    if days_inactive >= 5:
        pre_score += 15
        flags.append(f"Inactive for {days_inactive} days")

    if avg_exam_score < 60 and avg_exam_score > 0:
        pre_score += 15
        flags.append(f"Practice exam avg: {avg_exam_score}%")

    if days_to_exam is not None and days_to_exam <= 14 and study_hours_last_14d < 10:
        pre_score += 10
        flags.append(f"Insufficient study hours ({study_hours_last_14d}h) with exam in {days_to_exam} days")

    pre_score = min(100, pre_score)

    return {
        "topic_scores": topic_score_map,
        "weak_topics": weak_topics,
        "lab_completion_rate": lab_completion_rate,
        "labs_completed": labs_completed,
        "days_inactive": days_inactive,
        "recent_exam_scores": recent_exam_scores,
        "avg_exam_score": avg_exam_score,
        "study_hours_last_14d": study_hours_last_14d,
        "days_to_exam": days_to_exam,
        "pre_risk_score": pre_score,
        "pre_risk_flags": flags,
    }


def signals_to_risk_level(pre_score: int) -> str:
    if pre_score >= 55:
        return "HIGH"
    elif pre_score >= 30:
        return "MEDIUM"
    return "LOW"
