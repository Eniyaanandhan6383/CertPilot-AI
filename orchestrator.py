"""
CertPilot AI — 7-Agent Reasoning Chain (Dynamic)
Accepts ANY employee profile via run_certpilot_chain(employee_data)
"""

import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

# ── Config ───────────────────────────────────────────────────────────────
API_KEY = os.environ["AZURE_AI_API_KEY"]
ENDPOINT = "https://eniyaanandhan91-4178-resource.services.ai.azure.com"
DEPLOY = "gpt-4.1-mini"
API_VERSION = "2025-03-01-preview"

URL = f"{ENDPOINT}/openai/deployments/{DEPLOY}/chat/completions?api-version={API_VERSION}"
HEADERS = {"api-key": API_KEY, "Content-Type": "application/json"}

EXAM_FEE_USD = 165
HOURLY_RATE_USD = 45

# ── Default profile (fallback if no input given — keeps old demo working) ──
DEFAULT_EMPLOYEE = {
    "name": "Priya Nair",
    "role": "Senior Cloud Architect",
    "target_cert": "AZ-305",
    "exam_date": "2026-06-28",
    "days_to_exam": 16,
    "completion_percent": 54,
    "study_days_per_week": 2.1,
    "lab_completion_percent": 41,
    "topic_scores": {
        "Identity & Governance": 42,
        "Networking": 38,
        "Monitoring & Security": 47,
        "Data Integration": 55,
        "Migration & Modernization": 52,
        "Compute & App Architecture": 71
    }
}


# ── Core agent caller ────────────────────────────────────────────────────
def call_agent(system_prompt, user_prompt, max_tokens=1800):
    body = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": 0.3,
        "response_format": {"type": "json_object"}
    }
    r = requests.post(URL, headers=HEADERS, json=body, timeout=120)
    r.raise_for_status()
    content = r.json()["choices"][0]["message"]["content"]
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"raw_output": content}


# ── Build grounding context from dynamic employee data ──────────────────
def build_employee_context(employee):
    topic_scores = employee.get("topic_scores", {})
    topic_lines = "\n".join(
        f"  - {topic}: {score}%" for topic, score in topic_scores.items()
    ) or "  (no topic scores provided)"

    quiz_avg = (sum(topic_scores.values()) / len(topic_scores)) if topic_scores else 0

    return f"""Employee Name: {employee.get('name', 'Unknown')}
Role: {employee.get('role', 'Unknown')}
Target Certification: {employee.get('target_cert', 'Unknown')}
Exam Date: {employee.get('exam_date', 'Not set')}
Days Remaining Until Exam: {employee.get('days_to_exam', 'Unknown')}
Overall Course Completion: {employee.get('completion_percent', 0)}%
Study Consistency: {employee.get('study_days_per_week', 0)} days/week
Lab Completion Rate: {employee.get('lab_completion_percent', 0)}%
Average Quiz Score Across Topics: {quiz_avg:.1f}%

Topic-wise Quiz Scores:
{topic_lines}
"""


# ── Agent system prompts (generic — no hardcoded names) ──────────────────

AGENT1_SYS = """You are the Workforce Skills Intelligence Agent for CertPilot AI.

Your job: Given an employee profile, identify skill gaps.

1. Use the topic-wise quiz scores provided in the profile.
2. Identify topics where the score is below 70% — these are skill gaps.
3. Output a JSON object with: employee_name, role, target_cert, skill_gaps
   (array of {topic, current_score, required_score, gap_severity}).
   gap_severity is HIGH if score < 50, MEDIUM if 50-69, otherwise not a gap.

Ground every number strictly in the provided profile. Do not invent scores."""

AGENT2_SYS = """You are the Adaptive Learning Agent for CertPilot AI.

Your job: Take the skill gaps identified for the employee and generate a
personalized, week-by-week study plan.

1. Prioritize topics by gap_severity (HIGH gaps first).
2. Generate a 4-week study plan with: week number, focus topics,
   recommended resources, daily time commitment, and learning objectives.
3. For HIGH severity gaps, allocate at least 3 sessions per week.
4. Output JSON with: employee_name, exam_date, study_plan
   (array of {week, focus_topics, resources, daily_hours, objectives}).

Base all scheduling on the employee's actual study consistency from the profile.
Do not invent availability or scores."""

AGENT3_SYS = """You are the Assessment Agent for CertPilot AI.

Your job: Generate practice questions for the employee's weak topics and
produce topic-wise readiness scores.

1. For each topic scoring below 70%, generate 2 practice questions
   (scenario-based, matching the style of the target certification exam).
2. Calculate a readiness score per topic based on quiz performance and
   study completion %.
3. Output JSON with:
   - topic_readiness: array of {topic, score_percent, readiness_level
     (Ready/At Risk/Critical)}
   - practice_questions: array of {topic, question, options (A-D),
     correct_answer, explanation}
   - overall_readiness_score: weighted average

Ground all scores in the profile data. Questions must reflect realistic
exam domains for the target certification."""

AGENT4_SYS = """You are the Certification Risk Agent for CertPilot AI.
You are the most critical agent in the chain.

Your job: Reason over multiple signals to predict the employee's exam
failure risk.

From the profile, analyze ALL of the following signals:
1. Topic-wise quiz scores (especially topics below 50%)
2. Overall course completion percentage
3. Study consistency (days studied per week)
4. Lab activity completion rate
5. Days remaining until exam date

Apply this scoring logic:
- Quiz avg below 55% -> HIGH risk contribution
- Completion below 60% -> HIGH risk contribution
- Study consistency below 3 days/week -> MEDIUM risk contribution
- Lab completion below 50% -> HIGH risk contribution
- Less than 14 days to exam with HIGH signals -> escalate to HIGH

Output JSON:
{
  "employee_name": "...",
  "target_cert": "...",
  "risk_level": "HIGH | MEDIUM | LOW",
  "risk_score": 0-100,
  "risk_reasons": ["specific grounded reason 1", "specific grounded reason 2"],
  "weakest_topics": ["topic1", "topic2"],
  "confidence": "HIGH | MEDIUM"
}

You MUST cite specific numbers from the profile for every risk reason.
Never guess."""

AGENT5_SYS = """You are the Intervention Strategy Agent for CertPilot AI.

Your job: Take the risk prediction from the risk agent and convert it into
a concrete, actionable intervention plan.

1. For each high-risk area, prescribe a specific intervention:
   - Which resource/bootcamp to assign
   - How many additional study hours needed
   - Whether to delay the exam (and by how many days)
   - Which topics need 1:1 coaching vs self-study
2. Set a re-assessment checkpoint date.
3. Prioritize interventions by impact (highest ROI first).

Output JSON:
{
  "employee_name": "...",
  "risk_level": "...",
  "interventions": [
    {"priority": 1, "topic": "...", "action": "...", "resource": "...",
     "additional_hours": number, "delivery_mode": "self-study | bootcamp | coaching"}
  ],
  "exam_recommendation": "proceed | delay",
  "recommended_delay_days": number or null,
  "reassessment_date": "YYYY-MM-DD",
  "expected_risk_after_intervention": "HIGH | MEDIUM | LOW"
}

Ground every intervention in the employee's actual weak topics. Be specific,
not generic. If risk_level is LOW, exam_recommendation should be "proceed"
and interventions can be light/optional."""

AGENT6_SYS = """You are the Manager Intelligence Agent for CertPilot AI.

Your job: Produce a concise, manager-facing summary using the risk and
intervention outputs.

1. Summarize in manager-friendly language (no technical jargon).
2. Highlight what action the manager needs to take TODAY.
3. Show expected pass rate impact if interventions are followed vs ignored.

Output JSON:
{
  "manager_summary": {
    "team_size": 1,
    "employees_at_risk": 0 or 1,
    "expected_pass_rate_current": "percentage",
    "expected_pass_rate_after_intervention": "percentage"
  },
  "at_risk_employees": [
    {"name": "...", "cert": "...", "risk_level": "...",
     "risk_summary": "2-sentence plain English summary",
     "manager_action_required": "specific action this week",
     "deadline": "YYYY-MM-DD",
     "estimated_cost_if_fails": "exam retake cost + lost productivity estimate"}
  ],
  "recommended_manager_actions": ["Action 1 — specific and time-bound", "Action 2 — specific and time-bound"]
}

Write risk summaries in plain English avoiding ML/AI terminology. If risk
is LOW, at_risk_employees can be an empty array."""

AGENT7_SYS = f"""You are the Program Optimizer Agent for CertPilot AI.

Your job: Perform root-cause analysis on the certification program for this
employee/topic data and recommend structural improvements.

1. Identify which topics have the highest failure concentration.
2. Determine if the failure pattern looks systemic vs individual.
3. Calculate estimated wasted spend on failed/at-risk certifications.
4. Recommend program-level changes (not just individual interventions).

Apply this analysis framework:
- If a topic score is below 50% -> potential systemic gap, curriculum change needed
- If study time is below what the topic's difficulty/weight implies -> structural under-investment
- If lab completion is consistently low -> lab access/scheduling issue, not motivation

Output JSON:
{{
  "program_name": "Certification Readiness Program",
  "overall_program_health": "AT RISK | HEALTHY | CRITICAL",
  "systemic_gaps": [
    {{"topic": "...", "avg_score": "percentage", "root_cause": "...",
      "recommendation": "specific program-level fix"}}
  ],
  "estimated_wasted_spend": {{
    "failed_exam_retakes": "USD amount",
    "lost_productivity_hours": number,
    "total_estimated_waste": "USD amount"
  }},
  "program_recommendations": ["Recommendation 1", "Recommendation 2", "Recommendation 3"],
  "priority_action": "single most impactful change to make this month"
}}

Base cost estimates on: exam fee = ${EXAM_FEE_USD}, average employee hourly
rate = ${HOURLY_RATE_USD}. Show your math in root_cause fields."""


# ── Agent functions ────────────────────────────────────────────────────
def agent1_workforce_skills(context):
    return call_agent(AGENT1_SYS, f"Employee profile:\n{context}\n\nIdentify skill gaps.")


def agent2_adaptive_learning(context, a1):
    return call_agent(
        AGENT2_SYS,
        f"Employee profile:\n{context}\n\nSkill gaps from Agent 1:\n{json.dumps(a1)}\n\nGenerate the 4-week study plan."
    )


def agent3_assessment(context, a1):
    return call_agent(
        AGENT3_SYS,
        f"Employee profile:\n{context}\n\nSkill gaps from Agent 1:\n{json.dumps(a1)}\n\nGenerate readiness scores and practice questions."
    )


def agent4_cert_risk(context, a1, a3):
    return call_agent(
        AGENT4_SYS,
        f"Employee profile:\n{context}\n\nSkill gaps:\n{json.dumps(a1)}\n\nAssessment:\n{json.dumps(a3)}\n\nPredict the failure risk."
    )


def agent5_intervention(context, a4):
    return call_agent(
        AGENT5_SYS,
        f"Employee profile:\n{context}\n\nRisk prediction:\n{json.dumps(a4)}\n\nGenerate the intervention plan."
    )


def agent6_manager(context, a4, a5):
    return call_agent(
        AGENT6_SYS,
        f"Employee profile:\n{context}\n\nRisk prediction:\n{json.dumps(a4)}\n\nIntervention plan:\n{json.dumps(a5)}\n\nGenerate the manager dashboard summary."
    )


def agent7_optimizer(context, a4, a5):
    return call_agent(
        AGENT7_SYS,
        f"Employee profile:\n{context}\n\nRisk prediction:\n{json.dumps(a4)}\n\nIntervention plan:\n{json.dumps(a5)}\n\nGenerate the program-level analysis."
    )


# ── Main entry point — now accepts dynamic employee data ────────────────
def run_certpilot_chain(employee_data=None):
    """
    employee_data: dict matching DEFAULT_EMPLOYEE schema, or None to use
    the default demo profile (Priya Nair).
    """
    if not employee_data:
        employee_data = DEFAULT_EMPLOYEE

    context = build_employee_context(employee_data)

    print("\nCertPilot AI — 7-Agent Reasoning Chain")
    print(f"   Employee: {employee_data.get('name')} | Cert: {employee_data.get('target_cert')}")
    print("=" * 60)

    print("Running Agent 1 — Workforce Skills...")
    a1 = agent1_workforce_skills(context)

    print("Running Agent 2 — Adaptive Learning...")
    a2 = agent2_adaptive_learning(context, a1)

    print("Running Agent 3 — Assessment...")
    a3 = agent3_assessment(context, a1)

    print("Running Agent 4 — Certification Risk...")
    a4 = agent4_cert_risk(context, a1, a3)

    print("Running Agent 5 — Intervention...")
    a5 = agent5_intervention(context, a4)

    print("Running Agent 6 — Manager Intelligence...")
    a6 = agent6_manager(context, a4, a5)

    print("Running Agent 7 — Program Optimizer...")
    a7 = agent7_optimizer(context, a4, a5)

    full_output = {
        "certpilot_ai_chain": {
            "metadata": {
                "employee": employee_data.get("name"),
                "role": employee_data.get("role"),
                "cert": employee_data.get("target_cert"),
                "model": DEPLOY,
                "agents_run": 7
            },
            "input_profile": employee_data,
            "chain_outputs": {
                "agent1_skill_gaps": a1,
                "agent2_study_plan": a2,
                "agent3_assessment": a3,
                "agent4_risk_prediction": a4,
                "agent5_intervention": a5,
                "agent6_manager_dashboard": a6,
                "agent7_program_optimizer": a7
            }
        }
    }

    with open("certpilot_output.json", "w", encoding="utf-8") as f:
        json.dump(full_output, f, indent=2)

    print("\nFull chain complete!")
    print(f"   Risk Level:          {a4.get('risk_level', 'N/A')}")
    print(f"   Risk Score:          {a4.get('risk_score', 'N/A')}/100")
    print(f"   Exam Recommendation: {a5.get('exam_recommendation', 'N/A')}")
    print(f"   Program Health:      {a7.get('overall_program_health', 'N/A')}")

    return full_output


if __name__ == "__main__":
    run_certpilot_chain()
