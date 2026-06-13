"""
CertPilot AI — Agent Implementations
Each function = one agent call. Returns structured dict.
"""
import json
from database import get_db
from services.foundry_client import call_agent
from services.risk_scorer import compute_risk_signals, signals_to_risk_level
from agents.prompts import (
    SKILLS_INTELLIGENCE_PROMPT,
    RISK_INTELLIGENCE_PROMPT,
    INTERVENTION_STRATEGY_PROMPT,
    ADAPTIVE_LEARNING_PROMPT,
    ASSESSMENT_PROMPT,
    MANAGER_INTELLIGENCE_PROMPT,
    PROGRAM_OPTIMIZER_PROMPT,
)


# ── Helpers ────────────────────────────────────────────────────────────────

def _get_employee(employee_id: int) -> dict:
    db = get_db()
    row = db.execute(
        "SELECT * FROM employees WHERE id = ?", (employee_id,)
    ).fetchone()
    db.close()
    if not row:
        raise ValueError(f"Employee {employee_id} not found")
    return dict(row)


def _get_cert(certification_id: int) -> dict:
    db = get_db()
    row = db.execute(
        "SELECT * FROM certifications WHERE id = ?", (certification_id,)
    ).fetchone()
    db.close()
    if not row:
        raise ValueError(f"Certification {certification_id} not found")
    return dict(row)


def _get_cert_by_code(code: str) -> dict:
    db = get_db()
    row = db.execute(
        "SELECT * FROM certifications WHERE code = ?", (code,)
    ).fetchone()
    db.close()
    if not row:
        raise ValueError(f"Certification {code} not found")
    return dict(row)


# ── Agent 1: Workforce Skills Intelligence ─────────────────────────────────

def run_skills_intelligence(
    employee_id: int,
    current_cert_code: str | None,
    target_cert_code: str,
) -> dict:
    emp = _get_employee(employee_id)
    target_cert = _get_cert_by_code(target_cert_code)
    current_cert_name = current_cert_code or "None"

    user_msg = f"""
Employee Profile:
- Name: {emp['name']}
- Role: {emp['role']}
- Department: {emp['department']}
- Current Certification: {current_cert_name}
- Target Certification: {target_cert['code']} — {target_cert['name']} ({target_cert['level']})

Analyze the skill gaps between this employee's current state and the target certification requirements.
Generate a realistic learning path.
"""
    result = call_agent(SKILLS_INTELLIGENCE_PROMPT, user_msg)
    result["agent"] = "skills_intelligence"
    result["employee_id"] = employee_id
    result["target_cert"] = target_cert_code
    return result


# ── Agent 2: Certification Risk Intelligence ───────────────────────────────

def run_risk_intelligence(employee_id: int, certification_id: int) -> dict:
    emp = _get_employee(employee_id)
    cert = _get_cert(certification_id)
    signals = compute_risk_signals(employee_id, certification_id)

    user_msg = f"""
Employee: {emp['name']} ({emp['role']}, {emp['department']})
Target Certification: {cert['code']} — {cert['name']}

Learning Signal Data:
- Topic quiz scores: {json.dumps(signals['topic_scores'], indent=2)}
- Weak topics (score < 60%): {signals['weak_topics']}
- Lab completion rate: {signals['lab_completion_rate']}%
- Labs completed: {signals['labs_completed']}
- Days inactive (no study): {signals['days_inactive']}
- Recent practice exam scores: {signals['recent_exam_scores']}
- Average practice exam score: {signals['avg_exam_score']}%
- Study hours in last 14 days: {signals['study_hours_last_14d']}h
- Days to exam: {signals['days_to_exam']}
- Pre-computed risk score: {signals['pre_risk_score']}/100
- Pre-computed risk flags: {signals['pre_risk_flags']}

Analyze these signals and predict the certification failure risk with full reasoning.
"""
    result = call_agent(RISK_INTELLIGENCE_PROMPT, user_msg)
    result["agent"] = "risk_intelligence"
    result["employee_id"] = employee_id
    result["certification_id"] = certification_id
    result["computed_signals"] = signals

    # Persist to DB
    db = get_db()
    db.execute("""
        INSERT OR REPLACE INTO risk_assessments
        (employee_id, certification_id, risk_level, risk_score, risk_reasons, weak_topics)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        employee_id,
        certification_id,
        result.get("risk_level", signals_to_risk_level(signals["pre_risk_score"])),
        result.get("risk_score", signals["pre_risk_score"]),
        json.dumps(result.get("risk_reasons", [])),
        json.dumps(result.get("weak_topics", signals["weak_topics"])),
    ))
    db.commit()
    db.close()

    return result


# ── Agent 3: Intervention Strategy ────────────────────────────────────────

def run_intervention_strategy(employee_id: int, certification_id: int, risk_data: dict) -> dict:
    emp = _get_employee(employee_id)
    cert = _get_cert(certification_id)

    user_msg = f"""
Employee: {emp['name']} ({emp['role']})
Certification: {cert['code']} — {cert['name']}
Exam Date: {risk_data.get('computed_signals', {}).get('days_to_exam', 'unknown')} days away

Risk Assessment:
- Risk Level: {risk_data.get('risk_level')}
- Risk Score: {risk_data.get('risk_score')}/100
- Risk Reasons: {json.dumps(risk_data.get('risk_reasons', []), indent=2)}
- Weak Topics: {risk_data.get('weak_topics', [])}
- Strengths: {risk_data.get('strengths', [])}
- Time Pressure: {risk_data.get('time_pressure', 'unknown')}
- Reasoning: {risk_data.get('reasoning_chain', '')}

Generate specific intervention recommendations that will improve this employee's chance of passing.
"""
    result = call_agent(INTERVENTION_STRATEGY_PROMPT, user_msg)
    result["agent"] = "intervention_strategy"
    result["employee_id"] = employee_id
    result["certification_id"] = certification_id
    return result


# ── Agent 4: Adaptive Learning ─────────────────────────────────────────────

def run_adaptive_learning(
    employee_id: int,
    certification_id: int,
    skill_gaps: list[dict],
    daily_hours: float,
    days_to_exam: int,
) -> dict:
    emp = _get_employee(employee_id)
    cert = _get_cert(certification_id)

    user_msg = f"""
Employee: {emp['name']} ({emp['role']})
Certification: {cert['code']} — {cert['name']}
Available Study Time: {daily_hours} hours/day
Days Until Exam: {days_to_exam}

Identified Skill Gaps:
{json.dumps(skill_gaps, indent=2)}

Generate a realistic, adaptive study plan that prioritizes weak areas and builds toward exam readiness.
"""
    result = call_agent(ADAPTIVE_LEARNING_PROMPT, user_msg)
    result["agent"] = "adaptive_learning"
    result["employee_id"] = employee_id
    result["certification_id"] = certification_id

    # Persist plan
    db = get_db()
    db.execute("""
        INSERT INTO study_plans (employee_id, certification_id, daily_hours, plan_data_json)
        VALUES (?, ?, ?, ?)
    """, (employee_id, certification_id, daily_hours, json.dumps(result)))
    db.commit()
    db.close()

    return result


# ── Agent 5: Assessment ────────────────────────────────────────────────────

def run_assessment(employee_id: int, certification_id: int, weak_topics: list[str]) -> dict:
    emp = _get_employee(employee_id)
    cert = _get_cert(certification_id)
    signals = compute_risk_signals(employee_id, certification_id)

    user_msg = f"""
Employee: {emp['name']}
Certification: {cert['code']} — {cert['name']}
Topics to assess: {weak_topics}
Current topic scores: {json.dumps(signals['topic_scores'], indent=2)}
Recent practice exam scores: {signals['recent_exam_scores']}

Generate targeted practice questions for the weak topics and provide an overall readiness assessment.
"""
    result = call_agent(ASSESSMENT_PROMPT, user_msg)
    result["agent"] = "assessment"
    result["employee_id"] = employee_id
    result["certification_id"] = certification_id
    return result


# ── Agent 6: Manager Intelligence ─────────────────────────────────────────

def run_manager_intelligence(manager_id: int) -> dict:
    db = get_db()

    # Get all direct reports
    team = db.execute(
        "SELECT * FROM employees WHERE manager_id = ?", (manager_id,)
    ).fetchall()

    if not team:
        return {"error": "No team found for this manager", "agent": "manager_intelligence"}

    manager = db.execute(
        "SELECT * FROM employees WHERE id = ?", (manager_id,)
    ).fetchone()

    # Get latest risk assessment for each team member
    team_risk_data = []
    for emp in team:
        risk = db.execute("""
            SELECT r.*, c.code as cert_code, c.name as cert_name, ec.target_exam_date
            FROM risk_assessments r
            JOIN certifications c ON r.certification_id = c.id
            JOIN employee_certifications ec ON ec.employee_id = r.employee_id
                AND ec.certification_id = r.certification_id
            WHERE r.employee_id = ?
            ORDER BY r.assessed_at DESC LIMIT 1
        """, (emp["id"],)).fetchone()

        if risk:
            team_risk_data.append({
                "employee_name": emp["name"],
                "role": emp["role"],
                "certification": risk["cert_code"],
                "risk_level": risk["risk_level"],
                "risk_score": risk["risk_score"],
                "exam_date": risk["target_exam_date"],
                "weak_topics": json.loads(risk["weak_topics"]) if risk["weak_topics"] else [],
            })

    db.close()

    if not team_risk_data:
        return {
            "error": "No risk assessments found. Run risk analysis for team members first.",
            "agent": "manager_intelligence",
            "team_size": len(team),
        }

    user_msg = f"""
Manager: {dict(manager)['name']} ({dict(manager)['role']})
Department: {dict(manager)['department']}
Team Size: {len(team)}

Team Risk Data:
{json.dumps(team_risk_data, indent=2)}

Generate manager-level insights and recommended actions for this team's certification program.
"""
    result = call_agent(MANAGER_INTELLIGENCE_PROMPT, user_msg)
    result["agent"] = "manager_intelligence"
    result["manager_id"] = manager_id
    result["team_size"] = len(team)
    return result


# ── Agent 7: Program Optimizer ─────────────────────────────────────────────

def run_program_optimizer() -> dict:
    db = get_db()

    # Aggregate stats per certification
    cert_stats = db.execute("""
        SELECT
            c.code,
            c.name,
            COUNT(DISTINCT ec.employee_id) as enrolled,
            AVG(r.risk_score) as avg_risk_score,
            SUM(CASE WHEN r.risk_level = 'HIGH' THEN 1 ELSE 0 END) as high_risk_count,
            SUM(CASE WHEN r.risk_level = 'MEDIUM' THEN 1 ELSE 0 END) as medium_risk_count,
            SUM(CASE WHEN r.risk_level = 'LOW' THEN 1 ELSE 0 END) as low_risk_count
        FROM certifications c
        JOIN employee_certifications ec ON ec.certification_id = c.id
        LEFT JOIN risk_assessments r ON r.certification_id = c.id
            AND r.employee_id = ec.employee_id
        GROUP BY c.id
    """).fetchall()

    # Top weak topics across all employees
    weak_topic_agg = db.execute("""
        SELECT topic, AVG(score) as avg_score, COUNT(*) as total_attempts
        FROM learning_activities
        WHERE activity_type = 'quiz' AND score IS NOT NULL
        GROUP BY topic
        HAVING avg_score < 65
        ORDER BY avg_score ASC
        LIMIT 10
    """).fetchall()

    # Lab completion stats
    lab_stats = db.execute("""
        SELECT
            AVG(CASE WHEN activity_type = 'lab' THEN 1.0 ELSE 0 END) as lab_rate,
            AVG(CASE WHEN activity_type = 'practice_exam' THEN score ELSE NULL END) as avg_exam_score
        FROM learning_activities
    """).fetchone()

    db.close()

    cert_data = [dict(row) for row in cert_stats]
    weak_topics = [{"topic": r["topic"], "avg_score": round(r["avg_score"], 1),
                    "attempts": r["total_attempts"]} for r in weak_topic_agg]

    user_msg = f"""
Organization Certification Program Data:

Certification Enrollment & Risk:
{json.dumps(cert_data, indent=2)}

Weak Topics Across All Employees (avg quiz score < 65%):
{json.dumps(weak_topics, indent=2)}

Lab & Exam Stats:
- Overall lab activity rate: {dict(lab_stats).get('lab_rate', 0):.1%}
- Average practice exam score: {dict(lab_stats).get('avg_exam_score', 0):.1f}%

Analyze the certification program health and recommend organizational improvements.
"""
    result = call_agent(PROGRAM_OPTIMIZER_PROMPT, user_msg)
    result["agent"] = "program_optimizer"
    return result
