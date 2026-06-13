"""
CertPilot AI — Employee Router
Provides employee data endpoints for the React dashboard.
"""
from fastapi import APIRouter, HTTPException
from database import get_db
import json

router = APIRouter()


@router.get("/")
def list_employees():
    db = get_db()
    rows = db.execute("SELECT * FROM employees").fetchall()
    db.close()
    return [dict(r) for r in rows]


@router.get("/{employee_id}")
def get_employee(employee_id: int):
    db = get_db()
    row = db.execute("SELECT * FROM employees WHERE id = ?", (employee_id,)).fetchone()
    db.close()
    if not row:
        raise HTTPException(status_code=404, detail="Employee not found")
    return dict(row)


@router.get("/{employee_id}/certifications")
def get_employee_certifications(employee_id: int):
    db = get_db()
    rows = db.execute("""
        SELECT ec.*, c.code, c.name, c.level, c.passing_score
        FROM employee_certifications ec
        JOIN certifications c ON ec.certification_id = c.id
        WHERE ec.employee_id = ?
    """, (employee_id,)).fetchall()
    db.close()
    return [dict(r) for r in rows]


@router.get("/{employee_id}/activities")
def get_employee_activities(employee_id: int, limit: int = 50):
    db = get_db()
    rows = db.execute("""
        SELECT la.*, c.code as cert_code
        FROM learning_activities la
        JOIN certifications c ON la.certification_id = c.id
        WHERE la.employee_id = ?
        ORDER BY la.completed_at DESC
        LIMIT ?
    """, (employee_id, limit)).fetchall()
    db.close()
    return [dict(r) for r in rows]


@router.get("/{employee_id}/risk")
def get_employee_risk(employee_id: int):
    db = get_db()
    row = db.execute("""
        SELECT r.*, c.code, c.name
        FROM risk_assessments r
        JOIN certifications c ON r.certification_id = c.id
        WHERE r.employee_id = ?
        ORDER BY r.assessed_at DESC LIMIT 1
    """, (employee_id,)).fetchone()
    db.close()
    if not row:
        return {"message": "No risk assessment found. Run /agents/risk-intelligence first."}
    result = dict(row)
    result["risk_reasons"] = json.loads(result["risk_reasons"]) if result["risk_reasons"] else []
    result["weak_topics"] = json.loads(result["weak_topics"]) if result["weak_topics"] else []
    return result


@router.get("/dashboard/overview")
def dashboard_overview():
    """Aggregate data for the main React dashboard."""
    db = get_db()

    total_employees = db.execute("SELECT COUNT(*) FROM employees").fetchone()[0]
    total_enrollments = db.execute("SELECT COUNT(*) FROM employee_certifications").fetchone()[0]

    risk_counts = db.execute("""
        SELECT risk_level, COUNT(*) as count
        FROM risk_assessments
        WHERE id IN (
            SELECT MAX(id) FROM risk_assessments GROUP BY employee_id
        )
        GROUP BY risk_level
    """).fetchall()

    risk_summary = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for row in risk_counts:
        risk_summary[row["risk_level"]] = row["count"]

    cert_breakdown = db.execute("""
        SELECT c.code, c.name, COUNT(ec.id) as enrolled
        FROM certifications c
        LEFT JOIN employee_certifications ec ON ec.certification_id = c.id
        GROUP BY c.id
    """).fetchall()

    recent_activities = db.execute("""
        SELECT e.name, la.activity_type, la.topic, la.score, la.completed_at
        FROM learning_activities la
        JOIN employees e ON la.employee_id = e.id
        ORDER BY la.completed_at DESC LIMIT 10
    """).fetchall()

    db.close()

    return {
        "total_employees": total_employees,
        "total_enrollments": total_enrollments,
        "risk_summary": risk_summary,
        "cert_breakdown": [dict(r) for r in cert_breakdown],
        "recent_activities": [dict(r) for r in recent_activities],
    }


@router.get("/dashboard/team/{manager_id}")
def team_dashboard(manager_id: int):
    """Team-level data for manager view."""
    db = get_db()

    team = db.execute(
        "SELECT * FROM employees WHERE manager_id = ?", (manager_id,)
    ).fetchall()

    if not team:
        raise HTTPException(status_code=404, detail="No team found for this manager")

    team_data = []
    for emp in team:
        risk = db.execute("""
            SELECT r.risk_level, r.risk_score, c.code as cert_code, ec.target_exam_date
            FROM risk_assessments r
            JOIN certifications c ON r.certification_id = c.id
            JOIN employee_certifications ec ON ec.employee_id = r.employee_id
                AND ec.certification_id = r.certification_id
            WHERE r.employee_id = ?
            ORDER BY r.assessed_at DESC LIMIT 1
        """, (emp["id"],)).fetchone()

        team_data.append({
            **dict(emp),
            "risk_level": risk["risk_level"] if risk else "UNKNOWN",
            "risk_score": risk["risk_score"] if risk else None,
            "cert_target": risk["cert_code"] if risk else None,
            "exam_date": risk["target_exam_date"] if risk else None,
        })

    db.close()
    return {"manager_id": manager_id, "team_size": len(team), "team": team_data}
