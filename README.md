# CertPilot AI 🎯
### Enterprise Certification Success Intelligence Platform

> Built for the **Microsoft Agents League Hackathon 2026** — Reasoning Agents Track

---

## 🚀 What is CertPilot AI?

CertPilot AI is a 7-agent intelligent platform built on **Microsoft Azure AI Foundry** that helps enterprises eliminate certification failures. The system identifies employees at risk of failing Microsoft certification exams, delivers personalized study plans, and provides managers with real-time analytics dashboards.

---

## 😟 The Problem

Enterprises invest heavily in Microsoft certification programs, yet **40-60% of employees fail on their first attempt**. Managers have no visibility into who is at risk, and employees receive no personalized guidance aligned to their specific knowledge gaps.

---

## ✅ Our Solution

A coordinated pipeline of **7 specialized AI agents** that work together to:
- Identify at-risk employees before they fail
- Diagnose specific knowledge gaps per exam domain
- Deliver personalized day-by-day certification coaching
- Give managers real-time team readiness dashboards

---

## 🤖 7-Agent Architecture

| Agent | Role |
|-------|------|
| 🔴 Risk Assessment Agent | Classifies employees as HIGH/MEDIUM/LOW risk |
| 🔍 Knowledge Gap Analyzer | Identifies weak topic areas vs exam domain weightings |
| 📅 Study Plan Agent | Generates day-by-day personalized study schedule |
| 📚 Resource Curator Agent | Recommends Microsoft Learn modules and practice tests |
| 📊 Progress Tracker Agent | Monitors completion and dynamically adjusts plans |
| 👔 Manager Insights Agent | Produces executive dashboard and team analytics |
| 🎯 Orchestrator Agent | Coordinates full pipeline and context passing between agents |

---

## 🎬 Live Demo Scenario

**Employee**: Priya Nair
**Exam**: AZ-305 (Azure Solutions Architect Expert)
**Risk Level**: 🔴 HIGH
**Days to Exam**: 21

POST `/run-chain` with Priya's profile triggers the full 7-agent chain — from risk detection to a personalized 30-day study plan with curated resources and a manager dashboard summary.

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| AI Platform | Microsoft Azure AI Foundry (gpt-4.1-mini) |
| Backend | FastAPI 0.111.0 (Python 3.12) |
| Orchestration | Custom multi-agent orchestrator (orchestrator.py) |
| Database | SQLite (database.py) |
| Frontend | HTML/JS Static Dashboard |
| Infrastructure | Azure Container Registry |
| API Style | REST (async FastAPI with ThreadPoolExecutor) |

---

## 📁 Project Structure
CertPilot-AI/

├── agents/               # 7 individual agent modules

├── routers/              # FastAPI route handlers

├── services/             # Business logic layer

├── static/               # Frontend dashboard (index.html)

├── data/                 # Sample employee data

├── main.py               # FastAPI app with /run-chain & /last-output endpoints

├── orchestrator.py       # Multi-agent pipeline coordinator

├── database.py           # Database connection and models

├── Dockerfile            # Container configuration

└── requirements.txt      # Python dependencies

---

## ⚡ API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Serves the frontend dashboard |
| GET | `/health` | Health check |
| POST | `/run-chain` | Triggers full 7-agent chain for an employee |
| GET | `/last-output` | Returns last saved chain output |

### Example Request
POST /run-chain

{

"name": "Priya Nair",

"role": "Cloud Architect",

"target_cert": "AZ-305",

"exam_date": "2026-07-15",

"days_to_exam": 21,

"completion_percent": 60,

"study_days_per_week": 3,

"lab_completion_percent": 50,

"topic_scores": {

"Identity & Governance": 42,

"Storage Solutions": 70,

"Compute Infrastructure": 55

}

}

---

## ⚡ Quick Start

### Prerequisites
- Python 3.12+
- Azure AI Foundry API key and endpoint

### Installation
git clone https://github.com/Eniyaanandhan6383/CertPilot-AI.git

cd CertPilot-AI

pip install -r requirements.txt

### Environment Variables

Create a `.env` file:
AZURE_FOUNDRY_ENDPOINT=your_foundry_endpoint

AZURE_FOUNDRY_API_KEY=your_api_key

MODEL_NAME=gpt-4.1-mini

### Run
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

Open `http://localhost:8000` to see the dashboard.

---

## 👥 Team

| Name | Role | GitHub |
|------|------|--------|
| Eniya | Azure AI Infrastructure + Agent Design | [@Eniyaanandhan6383](https://github.com/Eniyaanandhan6383) |
| Bhuvanesh | FastAPI Backend + Agent Implementation | [@Bhuvanesh-S03](https://github.com/Bhuvanesh-S03) |

---

## 🏆 Hackathon

**Event**: Microsoft AI Skills Fest — Agents League Hackathon 2026
**Track**: 🧠 Reasoning Agents (Microsoft Foundry)
**Submission Date**: June 14, 2026
**Prize Pool**: $55,000 USD

---

## 📄 License

MIT License

Go to your repo → Add file → Create new file → name it README.md → paste → Commit. Done!
