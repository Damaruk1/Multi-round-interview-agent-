import streamlit as st
import pdfplumber
from docx import Document
import io

st.set_page_config(page_title="Multi-Round Interview Agent", layout="wide")

# ------------------ SESSION STATE ------------------
if "level" not in st.session_state:
    st.session_state.level = 1

# ------------------ FILE READERS ------------------
def read_pdf(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text

def read_docx(file):
    doc = Document(file)
    return "\n".join(p.text for p in doc.paragraphs)

def read_txt(file):
    return file.read().decode("utf-8")

# ------------------ LEVEL 1 MODEL ------------------
def resume_screening(resume_text, role):
    skills = ["python", "api", "database", "sql", "cloud", "docker"]
    found = sum(1 for s in skills if s in resume_text.lower())

    skill_match = min(100, found / len(skills) * 100)
    structure = 100 if len(resume_text.split()) > 200 else 70
    keyword_coverage = min(100, found * 15)

    final_score = round((skill_match + structure + keyword_coverage) / 3, 2)
    passed = final_score >= 60

    return {
        "skill_match": round(skill_match, 2),
        "structure": structure,
        "keyword_coverage": round(keyword_coverage, 2),
        "score": final_score,
        "pass": passed
    }

# ------------------ LEVEL 2 MODEL ------------------
def technical_evaluation(apis, db, scale):
    score = (apis + db + scale) / 3
    passed = score >= 0.6
    return {
        "probability": round(score, 3),
        "pass": passed
    }

# ------------------ LEVEL 3 MODEL ------------------
def scenario_evaluation(answer):
    text = answer.lower()

    flow = any(w in text for w in ["first", "then", "finally"])
    tradeoff = any(w in text for w in ["tradeoff", "latency", "cost"])
    stability = any(w in text for w in ["monitor", "rollback", "reliability"])

    score = round((flow + tradeoff + stability) / 3 * 100, 2)
    passed = score >= 70

    return {
        "flow": flow,
        "tradeoff": tradeoff,
        "stability": stability,
        "score": score,
        "pass": passed
    }

# ==================================================
# =================== LEVEL 1 ======================
# ==================================================
if st.session_state.level == 1:
    st.title("📄 Level 1 — Resume Screening")

    role = st.selectbox("Role Applied For", ["Backend Engineer", "ML Engineer", "DevOps Engineer"])
    file = st.file_uploader("Upload Resume (PDF / DOCX / TXT)", type=["pdf", "docx", "txt"])

    if st.button("Run Resume Screening") and file:
        if file.type == "application/pdf":
            resume_text = read_pdf(file)
        elif file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            resume_text = read_docx(file)
        else:
            resume_text = read_txt(file)

        result = resume_screening(resume_text, role)
        st.session_state.level1 = result

    if "level1" in st.session_state:
        r = st.session_state.level1

        st.subheader("📊 Resume Screening Metrics")
        c1, c2, c3 = st.columns(3)
        c1.metric("Skill Match (%)", r["skill_match"])
        c2.metric("Structure (%)", r["structure"])
        c3.metric("Keyword Coverage (%)", r["keyword_coverage"])

        st.metric("Final Score", r["score"])

        if r["pass"]:
            st.success("✅ PASSED Resume Screening")
            if st.button("➡ Proceed to Technical Evaluation"):
                st.session_state.level = 2
                st.rerun()
        else:
            st.error("❌ FAILED Resume Screening")

# ==================================================
# =================== LEVEL 2 ======================
# ==================================================
elif st.session_state.level == 2:
    st.title("🧪 Level 2 — Technical Evaluation")

    apis = st.checkbox("Understands APIs & HTTP")
    db = st.checkbox("Understands Databases & Indexing")
    scale = st.checkbox("Understands Scalability & Caching")

    if st.button("Run Technical Evaluation"):
        result = technical_evaluation(apis, db, scale)
        st.session_state.level2 = result

    if "level2" in st.session_state:
        r = st.session_state.level2

        st.subheader("📊 Technical Metrics")
        st.metric("Pass Probability", r["probability"])

        if r["pass"]:
            st.success("✅ PASSED Technical Evaluation")
            if st.button("➡ Proceed to Scenario Evaluation"):
                st.session_state.level = 3
                st.rerun()
        else:
            st.error("❌ FAILED Technical Evaluation")

# ==================================================
# =================== LEVEL 3 ======================
# ==================================================
elif st.session_state.level == 3:
    st.title("🧠 Level 3 — Scenario Evaluation")

    answer = st.text_area(
        "Explain how you would design a scalable backend system",
        height=200
    )

    if st.button("Run Scenario Evaluation") and answer:
        result = scenario_evaluation(answer)
        st.session_state.level3 = result

    if "level3" in st.session_state:
        r = st.session_state.level3

        st.subheader("📊 Scenario Metrics")
        c1, c2, c3 = st.columns(3)
        c1.metric("Logical Flow", r["flow"])
        c2.metric("Trade-offs", r["tradeoff"])
        c3.metric("Stability Awareness", r["stability"])

        st.metric("Final Score", r["score"])

        if r["pass"]:
            st.success("🎉 FINAL VERDICT: SELECTED")
        else:
            st.error("❌ FINAL VERDICT: REJECTED")
