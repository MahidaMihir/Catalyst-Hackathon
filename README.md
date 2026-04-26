# 🎯 AI Skill Assessment & Personalised Learning Plan Agent

> **Catalyst Hackathon — Deccan AI**
> A solo-built AI agent that goes beyond resumes to test what candidates *actually* know — and tells them exactly how to close the gaps.

---

## 🧠 The Problem

A resume tells you what someone **claims** to know — not how well they actually know it.

Hiring managers waste hours on interviews only to discover skill gaps. Candidates waste weeks applying to roles they're not ready for. There's no fast, honest way to know where you actually stand.

**This agent fixes that.**

---

## 💡 What It Does

1. **Upload** your Resume (PDF or DOCX) and a Job Description
2. **AI extracts** all required skills from the JD automatically
3. **Conversational assessment** — the AI interviews you skill by skill, adapting its questions based on your answers (harder if strong, simpler if weak)
4. **Gap analysis** — scores each skill 1–10, compares against required threshold
5. **Personalised learning plan** — for every gap, generates specific resources, time estimates, and a practice project

---

## 🎬 Demo

> **Live URL:** [YOUR_RAILWAY_URL_HERE]
>
> **Demo Video:** [YOUR_VIDEO_LINK_HERE]

### Sample Flow

| Step | What happens |
|------|-------------|
| Upload | Resume PDF + paste Job Description |
| Extraction | AI identifies: Python, FastAPI, SQL, REST APIs, Communication |
| Assessment | 2–3 adaptive questions per skill |
| Results | Radar chart + scores + full learning plan |

---

## 🏗️ Architecture

```
User Browser
     │
     ▼
Streamlit Frontend (app.py)
     │
     ├── pdfplumber / python-docx   ← parse resume & JD files
     │
     └── OpenRouter API  ────────→  DeepSeek V3 (free tier)
              │
              ├── extract_skills()        → JSON list of skills
              ├── generate_opening_question() → interview question
              ├── evaluate_answer()       → score + follow-up
              └── generate_learning_plan() → resources + project
```

All session state stored in-memory via Streamlit session_state.
No database required. No backend server required.

---

## 🛠️ Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Frontend + Backend | Streamlit (Python) | Single-file full-stack, instant deployment |
| AI Model | DeepSeek V3 via OpenRouter | Free tier, strong reasoning |
| PDF Parsing | pdfplumber | Handles multi-column resume layouts |
| DOCX Parsing | python-docx | Microsoft Word resume support |
| Data Display | pandas + st.bar_chart | Skill score visualisation |
| Deployment | Railway.app | Free tier, auto-deploy from GitHub |

---

## ⚙️ How to Run Locally

### Prerequisites
- Python 3.11+
- An OpenRouter API key (free at [openrouter.ai](https://openrouter.ai))

### Steps

**1. Clone the repo**
```bash
git clone https://github.com/YOUR_USERNAME/skill-assessment-agent.git
cd skill-assessment-agent
```

**2. Install dependencies**
```bash
# Windows
py -m pip install -r requirements.txt

# Mac/Linux
pip install -r requirements.txt
```

**3. Run the app**
```bash
# Windows
py -m streamlit run app.py

# Mac/Linux
streamlit run app.py
```

**4. Open in browser**

Go to `http://localhost:8501` — the app will ask for your OpenRouter API key on first load.

---

## 🔑 Environment Variables

For local development, you can optionally create `.streamlit/secrets.toml`:

```toml
OPENROUTER_API_KEY = "sk-or-v1-your_key_here"
```

For Railway deployment, set this in the **Variables** tab:

| Variable | Value |
|----------|-------|
| `OPENROUTER_API_KEY` | `sk-or-v1-your_key_here` |

---

## 🚀 Deploy to Railway

1. Push this repo to GitHub
2. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Select this repo
4. Go to **Variables** → add `OPENROUTER_API_KEY`
5. Railway auto-deploys — live URL ready in ~2 minutes

The `Procfile` handles the start command automatically:
```
web: streamlit run app.py --server.port $PORT --server.address 0.0.0.0
```

---

## 📥 Sample Input

**Job Description (pasted as text):**
```
We are hiring a Python Backend Developer.
Required skills: Python, FastAPI, SQL, REST API design,
Docker, Git, Problem Solving, Communication.
```

**Resume:** Any PDF or DOCX resume file.

---

## 📤 Sample Output

```json
{
  "skills_extracted": ["Python", "FastAPI", "SQL", "Docker", "REST APIs", "Git"],
  "scores": [
    { "skill": "Python",  "score": 8, "reasoning": "Strong fundamentals, good examples given." },
    { "skill": "FastAPI", "score": 4, "reasoning": "Knows basics but unclear on dependency injection." },
    { "skill": "Docker",  "score": 3, "reasoning": "Limited hands-on experience." }
  ],
  "gap_analysis": [
    { "skill": "FastAPI", "score": 4, "required": 7, "gap": 3 },
    { "skill": "Docker",  "score": 3, "required": 7, "gap": 4 }
  ],
  "learning_plan": {
    "FastAPI": {
      "resources": ["FastAPI official docs", "TestDriven.io FastAPI course"],
      "time_estimate_weeks": 2,
      "practice_project": "Build a CRUD API with JWT auth and dependency injection"
    },
    "Docker": {
      "resources": ["Docker Getting Started docs", "TechWorld with Nana - Docker tutorial"],
      "time_estimate_weeks": 2,
      "practice_project": "Containerise your FastAPI app with Docker Compose"
    }
  }
}
```

---

## 🧩 Project Structure

```
skill-assessment-agent/
├── app.py              # entire application (single file)
├── requirements.txt    # Python dependencies
├── Procfile            # Railway start command
├── runtime.txt         # Python version for Railway
└── README.md           # this file
```

---

## ✨ Key Features

- **Adaptive questioning** — not a static quiz. Questions get harder or easier based on your answers.
- **End-to-end in one file** — no complex backend setup, no Docker required locally.
- **Works with any role** — paste any job description and it extracts the right skills automatically.
- **Actionable output** — the learning plan includes real resource links, time estimates in weeks, and a specific practice project per skill.
- **Download results** — export your full assessment as a text file.
- **Debug mode** — built-in API connection tester for troubleshooting.

---

## 📊 Judging Criteria Addressed

| Criterion | Weight | How this project addresses it |
|-----------|--------|-------------------------------|
| Works end-to-end | 20% | Full flow: upload → assess → results with live URL |
| Quality of core agent | 25% | Adaptive 2–3 question loop, evaluates weak/medium/strong |
| Quality of output | 20% | Structured scores, bar chart, detailed learning plan |
| Technical implementation | 15% | Clean single-file Python, OpenRouter API, robust JSON parsing |
| Innovation & creativity | 10% | Adaptive depth — harder questions for stronger answers |
| UX — is it usable? | 5% | Streamlit UI with chat bubbles, progress sidebar, spinners |
| Clean documented code | 5% | Commented sections, clear function names, debug mode |

---

## 👤 Author

**Mihirsinh Mahida**
Freelancer at Deccan AI · B.Tech Final Year
Built solo for the Catalyst Hackathon — April 2026

---

## 📄 License

MIT License — free to use, modify, and distribute.
