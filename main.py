"""
CertPilot AI — FastAPI Backend (Dynamic)
POST /run-chain with an employee profile JSON body to run the 7-agent
chain for ANY employee. Omit the body (or send {}) to run the default
demo profile.
"""

from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import json
import os
import asyncio
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from orchestrator import run_certpilot_chain

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="CertPilot AI", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

executor = ThreadPoolExecutor(max_workers=2)


# ── Routes ───────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return FileResponse(str(BASE_DIR / "static" / "index.html"))


# Mount static assets (css/js/images if you add any later)
static_dir = BASE_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/health")
def health():
    return {"status": "ok", "service": "CertPilot AI"}


@app.post("/run-chain")
async def run_chain(employee: dict = Body(default=None)):
    """
    Triggers the full 7-agent reasoning chain for the given employee profile.

    Expected body shape (all fields optional — missing ones fall back to
    the default demo profile):
    {
      "name": "Employee Name",
      "role": "Job Title",
      "target_cert": "AZ-305",
      "exam_date": "2026-07-15",
      "days_to_exam": 21,
      "completion_percent": 60,
      "study_days_per_week": 3,
      "lab_completion_percent": 50,
      "topic_scores": {
        "Topic A": 42,
        "Topic B": 70
      }
    }
    """
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(executor, run_certpilot_chain, employee)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/last-output")
def last_output():
    """
    Returns the last saved chain output without re-running anything.
    Useful for refreshing the dashboard after a page reload.
    """
    path = BASE_DIR / "certpilot_output.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="No output found. Run /run-chain first.")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {"status": "success", "data": data}
