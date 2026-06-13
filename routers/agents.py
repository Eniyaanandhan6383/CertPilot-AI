"""
CertPilot AI — Agent API Router
Exposes all 7 agents + the full orchestration chain.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from agents.agent_runners import (
    run_skills_intelligence,
    run_risk_intelligence,
    run_intervention_strategy,
    run_adaptive_learning,
    run_assessment,
    run_manager_intelligence,
    run_program_optimizer,
)

router = APIRouter()


# ── Request Models ─────────────────────────────────────────────────────────

class SkillsRequest(BaseModel):
    employee_id: int
    current_cert_code: str | None = None
    target_cert_code: str


class RiskRequest(BaseModel):
    employee_id: int
    certification_id: int


class InterventionRequest(BaseModel):
    employee_id: int
    certification_id: int


class LearningRequest(BaseModel):
    employee_id: int
    certification_id: int
    daily_hours: float = 1.5
    days_to_exam: int = 30


class AssessmentRequest(BaseModel):
    employee_id: int
    certification_id: int


class ManagerRequest(BaseModel):
    manager_id: int


class FullChainRequest(BaseModel):
    """Run all agents in sequence for one employee — demo endpoint."""
    employee_id: int
    certification_id: int
    current_cert_code: str | None = None
    target_cert_code: str
    daily_hours: float = 1.5
    manager_id: int | None = None


# ── Individual Agent Endpoints ─────────────────────────────────────────────

@router.post("/skills-intelligence")
async def skills_intelligence(req: SkillsRequest):
    """Agent 1: Identify skill gaps and recommend learning path."""
    try:
        return run_skills_intelligence(
            req.employee_id, req.current_cert_code, req.target_cert_code
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/risk-intelligence")
async def risk_intelligence(req: RiskRequest):
    """Agent 2: Predict certification failure risk from learning signals."""
    try:
        return run_risk_intelligence(req.employee_id, req.certification_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/intervention-strategy")
async def intervention_strategy(req: InterventionRequest):
    """Agent 3: Recommend interventions based on risk profile."""
    try:
        # First get risk data (run risk agent to get latest signals)
        risk_data = run_risk_intelligence(req.employee_id, req.certification_id)
        return run_intervention_strategy(req.employee_id, req.certification_id, risk_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/adaptive-learning")
async def adaptive_learning(req: LearningRequest):
    """Agent 4: Generate personalized adaptive study plan."""
    try:
        # Get skill gaps from Agent 1 first — use defaults if not available
        from database import get_db
        db = get_db()
        cert = db.execute(
            "SELECT code FROM certifications WHERE id = ?", (req.certification_id,)
        ).fetchone()
        db.close()

        skills_data = run_skills_intelligence(
            req.employee_id, None, cert["code"]
        )
        skill_gaps = skills_data.get("skill_gaps", [])

        return run_adaptive_learning(
            req.employee_id, req.certification_id,
            skill_gaps, req.daily_hours, req.days_to_exam
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/assessment")
async def assessment(req: AssessmentRequest):
    """Agent 5: Generate grounded practice questions and readiness score."""
    try:
        from services.risk_scorer import compute_risk_signals
        signals = compute_risk_signals(req.employee_id, req.certification_id)
        weak_topics = signals.get("weak_topics", [])
        if not weak_topics:
            # Assess all topics if none are specifically weak
            from database import get_db
            db = get_db()
            cert = db.execute(
                "SELECT code FROM certifications WHERE id = ?", (req.certification_id,)
            ).fetchone()
            db.close()
            from data.seed import CERT_TOPICS
            weak_topics = CERT_TOPICS.get(cert["code"], [])[:3]

        return run_assessment(req.employee_id, req.certification_id, weak_topics)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/manager-intelligence")
async def manager_intelligence(req: ManagerRequest):
    """Agent 6: Generate team-level certification insights for managers."""
    try:
        return run_manager_intelligence(req.manager_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/program-optimizer")
async def program_optimizer():
    """Agent 7: Analyze org-wide certification outcomes and recommend improvements."""
    try:
        return run_program_optimizer()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Full Orchestration Chain — Demo Endpoint ───────────────────────────────

@router.post("/full-chain")
async def full_chain(req: FullChainRequest):
    """
    Runs all agents in sequence for one employee.
    This is the demo endpoint — shows the complete reasoning chain.
    Steps: Skills → Risk → Intervention → Learning Plan → Assessment
    """
    results = {"employee_id": req.employee_id, "chain": []}

    try:
        # Step 1: Skills Intelligence
        step1 = run_skills_intelligence(
            req.employee_id, req.current_cert_code, req.target_cert_code
        )
        results["chain"].append({"step": 1, "agent": "skills_intelligence", "output": step1})

        # Step 2: Risk Intelligence (uses DB activity data)
        step2 = run_risk_intelligence(req.employee_id, req.certification_id)
        results["chain"].append({"step": 2, "agent": "risk_intelligence", "output": step2})

        # Step 3: Intervention Strategy (if risk is MEDIUM or HIGH)
        step3 = None
        if step2.get("risk_level") in ("HIGH", "MEDIUM"):
            step3 = run_intervention_strategy(req.employee_id, req.certification_id, step2)
            results["chain"].append({"step": 3, "agent": "intervention_strategy", "output": step3})

        # Step 4: Adaptive Learning Plan
        skill_gaps = step1.get("skill_gaps", [])
        step4 = run_adaptive_learning(
            req.employee_id, req.certification_id,
            skill_gaps, req.daily_hours,
            step2.get("computed_signals", {}).get("days_to_exam", 30)
        )
        results["chain"].append({"step": 4, "agent": "adaptive_learning", "output": step4})

        # Step 5: Assessment on weak topics
        weak_topics = step2.get("weak_topics", [])
        step5 = run_assessment(req.employee_id, req.certification_id, weak_topics)
        results["chain"].append({"step": 5, "agent": "assessment", "output": step5})

        # Step 6: Manager Intelligence (if manager_id provided)
        if req.manager_id:
            step6 = run_manager_intelligence(req.manager_id)
            results["chain"].append({"step": 6, "agent": "manager_intelligence", "output": step6})

        results["status"] = "completed"
        results["total_steps"] = len(results["chain"])
        results["risk_level"] = step2.get("risk_level")
        results["intervention_required"] = step3 is not None

        return results

    except Exception as e:
        results["status"] = "failed"
        results["error"] = str(e)
        raise HTTPException(status_code=500, detail=results)
