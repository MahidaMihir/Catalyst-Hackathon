import streamlit as st
import pdfplumber
import docx
import json
import re
import io
import time
from openai import OpenAI

st.set_page_config(page_title="AI Skill Assessment Agent", page_icon="🎯", layout="wide")

# ── API KEY ───────────────────────────────────────────────────────────────────
try:
    OPENROUTER_API_KEY = st.secrets.get("OPENROUTER_API_KEY", "")
except Exception:
    OPENROUTER_API_KEY = ""

if "or_key" in st.session_state and not OPENROUTER_API_KEY:
    OPENROUTER_API_KEY = st.session_state["or_key"]

if not OPENROUTER_API_KEY:
    st.title("🎯 AI Skill Assessment Agent")
    st.info("Enter your OpenRouter API key to begin. Get one free at openrouter.ai")
    key_input = st.text_input("OpenRouter API Key", type="password", placeholder="sk-or-v1-...")
    if key_input.strip():
        st.session_state["or_key"] = key_input.strip()
        st.rerun()
    st.stop()

# ── CLIENT ────────────────────────────────────────────────────────────────────
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

# Most reliable FREE model on OpenRouter
MODEL = "deepseek/deepseek-v3.2"

# ── FILE PARSING ──────────────────────────────────────────────────────────────
def extract_text_from_pdf(file_bytes: bytes) -> str:
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            return "\n".join(p.extract_text() or "" for p in pdf.pages)
    except Exception as e:
        return f"Error reading PDF: {e}"

def extract_text_from_docx(file_bytes: bytes) -> str:
    try:
        doc = docx.Document(io.BytesIO(file_bytes))
        return "\n".join(p.text for p in doc.paragraphs)
    except Exception as e:
        return f"Error reading DOCX: {e}"

def parse_uploaded_file(uploaded_file) -> str:
    name = uploaded_file.name.lower()
    raw  = uploaded_file.read()
    if name.endswith(".pdf"):
        return extract_text_from_pdf(raw)
    elif name.endswith(".docx"):
        return extract_text_from_docx(raw)
    elif name.endswith(".txt"):
        return raw.decode("utf-8", errors="ignore")
    return "Unsupported file type."

# ── AI CALL ───────────────────────────────────────────────────────────────────
def call_ai(prompt: str, debug_label: str = "") -> str:
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.3,
        )
        result = response.choices[0].message.content.strip()
        if st.session_state.get("debug_mode"):
            with st.expander(f"🐛 Debug: {debug_label}", expanded=False):
                st.text(f"Model: {MODEL}")
                st.text(f"Response:\n{result}")
        return result
    except Exception as e:
        error_msg = str(e)
        st.error(f"API Error: {error_msg}")
        if st.session_state.get("debug_mode"):
            with st.expander(f"🐛 Debug ERROR: {debug_label}", expanded=True):
                st.text(f"Full error: {error_msg}")
        return ""

def call_ai_json(prompt: str, debug_label: str = "") -> dict | list:
    raw = call_ai(prompt, debug_label)
    if not raw:
        return {}
    # strip markdown fences
    clean = re.sub(r"```(?:json)?|```", "", raw).strip()
    # try direct parse
    try:
        return json.loads(clean)
    except Exception:
        pass
    # try to extract JSON from response
    m = re.search(r"\{[^{}]*\}", clean, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    # last resort: find any array
    m2 = re.search(r"\[[^\[\]]*\]", clean, re.DOTALL)
    if m2:
        try:
            return json.loads(m2.group(0))
        except Exception:
            pass
    if st.session_state.get("debug_mode"):
        st.warning(f"Could not parse JSON from: {clean[:300]}")
    return {}

# ── CORE LOGIC ────────────────────────────────────────────────────────────────
def extract_skills(jd_text: str) -> list[str]:
    prompt = f"""Extract the required skills from this job description.
Reply with ONLY a JSON object. No explanation. No markdown. Just JSON.
Format: {{"skills": ["Skill1", "Skill2", "Skill3"]}}
List 5 to 12 skills. Use short human-readable names.

Job Description:
{jd_text[:2000]}

Reply with only the JSON object:"""
    result = call_ai_json(prompt, "extract_skills")
    if isinstance(result, dict) and "skills" in result:
        return result["skills"]
    # fallback: try parsing as list directly
    if isinstance(result, list):
        return result
    return []

def generate_opening_question(skill: str, all_skills: list[str]) -> str:
    prompt = f"""You are a technical interviewer. Ask ONE medium-difficulty interview question to test real knowledge of: {skill}
Only write the question. No introduction. No explanation.
Question:"""
    q = call_ai(prompt, f"opening_question_{skill}")
    return q or f"Can you explain your experience with {skill} and give a practical example?"

def evaluate_answer(skill: str, question: str, answer: str, q_count: int) -> dict:
    must_complete = q_count >= 2
    prompt = f"""You are evaluating a technical interview answer.
Skill: {skill}
Question: {question}
Answer: {answer}

{"Give a final score now - this is the last question for this skill." if must_complete else "Evaluate the answer."}

Reply with ONLY a JSON object. No explanation. No markdown.
{{"status": "complete", "score": 7, "reasoning": "one sentence", "next_question": null}}
OR if you need one more question:
{{"status": "continue", "strength": "medium", "score": null, "reasoning": null, "next_question": "your follow-up question here"}}

{"You MUST use status complete and give a score 1-10." if must_complete else ""}

JSON:"""
    result = call_ai_json(prompt, f"evaluate_{skill}")
    if not isinstance(result, dict) or "status" not in result:
        return {"status": "complete", "score": 6, "reasoning": "Assessment recorded.", "next_question": None}
    if must_complete and result.get("status") != "complete":
        result["status"] = "complete"
        result["score"] = result.get("score") or 6
        result["reasoning"] = result.get("reasoning") or "Assessment complete."
    return result

def generate_learning_plan_for_skill(skill: str, score: int, required: int, gap: int) -> dict:
    prompt = f"""Create a learning plan for someone who scored {score}/10 in {skill} and needs {required}/10.
Reply with ONLY a JSON object. No explanation. No markdown.
{{"skill": "{skill}", "what_to_learn": ["topic1", "topic2", "topic3"], "resources": [{{"title": "Resource Name", "url": "https://example.com", "type": "course", "duration": "10 hours"}}], "time_estimate_weeks": 3, "practice_project": "Build something with {skill}"}}

JSON:"""
    result = call_ai_json(prompt, f"learning_plan_{skill}")
    if not isinstance(result, dict) or "skill" not in result:
        return {
            "skill": skill,
            "what_to_learn": [f"Core {skill} fundamentals", f"Advanced {skill} patterns", "Real-world applications"],
            "resources": [{"title": f"{skill} Official Documentation", "url": "https://google.com", "type": "docs", "duration": "5 hours"}],
            "time_estimate_weeks": gap + 1,
            "practice_project": f"Build a small project using {skill}"
        }
    return result

# ── SESSION STATE ─────────────────────────────────────────────────────────────
defaults = {
    "step": "upload",
    "resume_text": "",
    "jd_text": "",
    "skills": [],
    "current_skill_idx": 0,
    "question_counts": {},
    "conversation": [],
    "current_question": "",
    "scores": [],
    "gap_analysis": [],
    "learning_plan": {},
    "debug_mode": False,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── STYLES ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.chat-user{background:#dbeafe;border-radius:12px 12px 2px 12px;padding:10px 14px;margin:6px 0;max-width:80%;margin-left:auto;}
.chat-bot{background:#f3f4f6;border-radius:12px 12px 12px 2px;padding:10px 14px;margin:6px 0;max-width:80%;}
</style>""", unsafe_allow_html=True)

# debug toggle in sidebar always
with st.sidebar:
    st.session_state.debug_mode = st.toggle("🐛 Debug mode", value=st.session_state.debug_mode)
    if st.session_state.debug_mode:
        st.info(f"Model: {MODEL}")
        st.info(f"Key: ...{OPENROUTER_API_KEY[-6:]}")
        if st.button("🧪 Test API connection"):
            with st.spinner("Testing..."):
                test = call_ai("Reply with the single word: working", "api_test")
            if test:
                st.success(f"API works! Response: {test}")
            else:
                st.error("API call failed. Check your key.")

# ═══════════════ STEP 1: UPLOAD ═══════════════════════════════════════════════
if st.session_state.step == "upload":
    st.title("🎯 AI Skill Assessment Agent")
    st.markdown("*Upload your Resume and a Job Description. The AI will assess your real skill proficiency and build a personalised learning plan.*")
    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📄 Your Resume")
        resume_file = st.file_uploader("Upload PDF, DOCX or TXT", type=["pdf","docx","txt"], key="resume_upload")

    with col2:
        st.subheader("💼 Job Description")
        jd_mode = st.radio("", ["Paste text", "Upload file"], horizontal=True, label_visibility="collapsed")
        if jd_mode == "Paste text":
            jd_text_input = st.text_area("Paste the job description here", height=200,
                placeholder="We are looking for a Python developer with experience in FastAPI, SQL...")
            jd_file_input = None
        else:
            jd_file_input = st.file_uploader("Upload JD", type=["pdf","docx","txt"], key="jd_upload")
            jd_text_input = ""

    st.divider()

    if st.button("🚀 Start Assessment", type="primary", use_container_width=True):
        errors = []
        if not resume_file:
            errors.append("Please upload your resume.")
        if jd_mode == "Paste text" and not jd_text_input.strip():
            errors.append("Please paste the job description.")
        if jd_mode == "Upload file" and not jd_file_input:
            errors.append("Please upload the job description file.")
        if errors:
            for e in errors:
                st.error(e)
        else:
            with st.spinner("Parsing documents..."):
                st.session_state.resume_text = parse_uploaded_file(resume_file)
                st.session_state.jd_text = (
                    jd_text_input.strip() if jd_mode == "Paste text"
                    else parse_uploaded_file(jd_file_input)
                )

            if st.session_state.debug_mode:
                st.write("JD text preview:", st.session_state.jd_text[:300])

            with st.spinner("Extracting skills from job description..."):
                skills = extract_skills(st.session_state.jd_text)

            if not skills:
                st.error("Could not extract skills. Turn on 🐛 Debug mode in the sidebar and try again to see the exact error.")
                st.stop()

            st.success(f"Found {len(skills)} skills: {', '.join(skills)}")
            with st.spinner("Generating first interview question..."):
                st.session_state.skills = skills
                st.session_state.question_counts = {s: 0 for s in skills}
                first_q = generate_opening_question(skills[0], skills)
                st.session_state.current_question = first_q
                st.session_state.conversation.append(
                    {"role": "assistant", "content": first_q, "skill": skills[0]}
                )
            st.session_state.step = "assess"
            st.rerun()

# ═══════════════ STEP 2: ASSESSMENT ═══════════════════════════════════════════
elif st.session_state.step == "assess":
    skills = st.session_state.skills
    idx    = st.session_state.current_skill_idx
    scores = st.session_state.scores

    with st.sidebar:
        st.markdown("### 📊 Skills")
        for i, skill in enumerate(skills):
            scored = next((s for s in scores if s["skill"] == skill), None)
            if scored:
                e = "🟢" if scored["score"] >= 7 else ("🟡" if scored["score"] >= 5 else "🔴")
                st.success(f"{e} {skill} — {scored['score']}/10")
            elif i == idx:
                st.info(f"▶ {skill}")
            else:
                st.markdown(f"○ {skill}")
        st.session_state.debug_mode = st.toggle("🐛 Debug mode", value=st.session_state.debug_mode, key="dbg2")

    current_skill = skills[idx] if idx < len(skills) else None
    st.title("💬 Skill Assessment")
    if current_skill:
        st.caption(f"Skill **{len(scores)+1}** of **{len(skills)}** — Assessing: **{current_skill}**")
    st.divider()

    for msg in st.session_state.conversation:
        if msg["role"] == "assistant":
            st.markdown(f'<div class="chat-bot">🤖 {msg["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="chat-user">👤 {msg["content"]}</div>', unsafe_allow_html=True)

    st.divider()

    if current_skill:
        with st.form("answer_form", clear_on_submit=True):
            user_answer = st.text_area("Your answer", placeholder="Type your answer here...", height=100)
            submitted = st.form_submit_button("Send ➤", type="primary", use_container_width=True)

        if submitted and user_answer.strip():
            st.session_state.conversation.append(
                {"role": "user", "content": user_answer.strip(), "skill": current_skill})
            q_count = st.session_state.question_counts.get(current_skill, 0)

            with st.spinner("Evaluating..."):
                evaluation = evaluate_answer(
                    current_skill, st.session_state.current_question,
                    user_answer.strip(), q_count)

            q_count += 1
            st.session_state.question_counts[current_skill] = q_count

            if evaluation.get("status") == "complete" or q_count >= 3:
                score     = evaluation.get("score") or 6
                reasoning = evaluation.get("reasoning") or "Assessment complete."
                st.session_state.scores.append(
                    {"skill": current_skill, "score": int(score), "reasoning": reasoning})
                st.session_state.current_skill_idx += 1
                next_idx = st.session_state.current_skill_idx

                if next_idx >= len(skills):
                    threshold = 7
                    gap_items = [
                        {"skill": s["skill"], "score": s["score"],
                         "required": threshold, "gap": max(0, threshold - s["score"])}
                        for s in st.session_state.scores
                    ]
                    st.session_state.gap_analysis = gap_items
                    with st.spinner("Generating your personalised learning plan..."):
                        plan_items = []
                        for item in gap_items:
                            if item["gap"] > 0:
                                plan = generate_learning_plan_for_skill(
                                    item["skill"], item["score"],
                                    item["required"], item["gap"])
                                plan["gap"] = item["gap"]
                                plan_items.append(plan)
                        st.session_state.learning_plan = {
                            "items": plan_items,
                            "total_time_estimate_weeks": sum(
                                p.get("time_estimate_weeks", 0) for p in plan_items),
                        }
                    st.session_state.step = "results"
                    st.rerun()
                else:
                    next_skill = skills[next_idx]
                    st.session_state.conversation.append(
                        {"role": "assistant", "content": f"Got it! Moving on to **{next_skill}**.", "skill": next_skill})
                    with st.spinner(f"Next question..."):
                        next_q = generate_opening_question(next_skill, skills)
                    st.session_state.current_question = next_q
                    st.session_state.conversation.append(
                        {"role": "assistant", "content": next_q, "skill": next_skill})
                    st.rerun()
            else:
                follow_up = evaluation.get("next_question") or generate_opening_question(current_skill, skills)
                st.session_state.current_question = follow_up
                st.session_state.conversation.append(
                    {"role": "assistant", "content": follow_up, "skill": current_skill})
                st.rerun()

# ═══════════════ STEP 3: RESULTS ══════════════════════════════════════════════
elif st.session_state.step == "results":
    gap_analysis  = st.session_state.gap_analysis
    learning_plan = st.session_state.learning_plan
    scores        = st.session_state.scores
    plan_items    = learning_plan.get("items", [])

    ready_pct = int(
        sum(1 for g in gap_analysis if g["gap"] == 0) /
        max(len(gap_analysis), 1) * 100)

    st.title("📈 Your Assessment Results")
    st.divider()

    c1, c2, c3 = st.columns(3)
    c1.metric("Job Readiness", f"{ready_pct}%")
    c2.metric("Skills Assessed", len(scores))
    c3.metric("Weeks to Close Gaps", learning_plan.get("total_time_estimate_weeks", 0))
    st.divider()

    st.subheader("📊 Skill Scores vs Required (7/10)")
    import pandas as pd
    st.bar_chart(pd.DataFrame([
        {"Skill": g["skill"], "Your Score": g["score"], "Required": g["required"]}
        for g in gap_analysis]).set_index("Skill"))

    st.subheader("🎯 Detailed Scores")
    cols = st.columns(min(len(scores), 3))
    for i, s in enumerate(scores):
        with cols[i % 3]:
            e = "🟢" if s["score"] >= 7 else ("🟡" if s["score"] >= 5 else "🔴")
            st.metric(f"{e} {s['skill']}", f"{s['score']}/10",
                delta=f"Gap: {max(0,7-s['score'])}" if s["score"]<7 else "Ready ✓",
                delta_color="inverse" if s["score"]<7 else "normal")
            st.caption(s.get("reasoning",""))

    st.divider()

    if plan_items:
        st.subheader("📚 Personalised Learning Plan")
        st.info(f"Total time to close all gaps: **{learning_plan['total_time_estimate_weeks']} weeks**")
        for item in plan_items:
            with st.expander(f"📖 {item.get('skill')} — Gap: {item.get('gap')} pts — Est. {item.get('time_estimate_weeks')} weeks", expanded=True):
                for t in item.get("what_to_learn", []):
                    st.markdown(f"• {t}")
                for r in item.get("resources", []):
                    st.markdown(f"🔗 [{r.get('title','Resource')}]({r.get('url','#')}) · {r.get('type','')} · {r.get('duration','')}")
                if item.get("practice_project"):
                    st.info(f"💡 **Practice project:** {item['practice_project']}")
    else:
        st.success("🎉 You already meet the required proficiency for all skills!")

    st.divider()

    lines = [f"# SKILL ASSESSMENT RESULTS\nJob Readiness: {ready_pct}%\n\n## SCORES"]
    for s in scores:
        lines.append(f"- {s['skill']}: {s['score']}/10 — {s.get('reasoning','')}")
    lines.append("\n## LEARNING PLAN")
    for item in plan_items:
        lines.append(f"\n### {item.get('skill')} ({item.get('time_estimate_weeks')} weeks)")
        for t in item.get("what_to_learn", []):
            lines.append(f"- {t}")
        for r in item.get("resources", []):
            lines.append(f"  * {r.get('title')} — {r.get('url')}")
        lines.append(f"Project: {item.get('practice_project','')}")

    st.download_button("⬇️ Download Results", data="\n".join(lines),
        file_name="assessment_results.txt", mime="text/plain", use_container_width=True)

    if st.button("🔄 Start New Assessment", use_container_width=True):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()
