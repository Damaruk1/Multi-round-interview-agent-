import streamlit as st
import pdfplumber
from docx import Document

from models.Level1screening import level1_screen
from models.Level2technical import level2_technical
from models.Level3scenario import level3_scenario

from db import (
    upsert_candidate,
    create_session,
    save_round_result,
    complete_session
)

# --------------------------------------------------
# Helpers
# --------------------------------------------------

def extract_text(uploaded_file):
    name = uploaded_file.name.lower()

    if name.endswith(".txt"):
        return uploaded_file.read().decode("utf-8", errors="ignore")

    if name.endswith(".pdf"):
        text = ""
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
        return text

    if name.endswith(".docx"):
        doc = Document(uploaded_file)
        return "\n".join(p.text for p in doc.paragraphs)

    raise ValueError("Unsupported file format")


# --------------------------------------------------
# Streamlit Setup
# --------------------------------------------------

st.set_page_config(
    page_title="Multi-Round Interview Agent",
    layout="centered"
)

st.title("🧠 Multi-Round Interview Agent")
st.markdown(
    """
This system evaluates candidates through **three sequential models**:

1️⃣ Resume Screening  
2️⃣ Technical Evaluation  
3️⃣ Scenario-Based Reasoning  

A candidate must **pass each stage** to proceed.
"""
)

# --------------------------------------------------
# Session State Init
# --------------------------------------------------

if "stage" not in st.session_state:
    st.session_state.stage = 1

# --------------------------------------------------
# Stage 1 — Resume Screening
# --------------------------------------------------

if st.session_state.stage == 1:
    st.header("📄 Level 1 — Resume Screening")

    role = st.selectbox(
        "Role Applied For",
        ["Backend Engineer", "Data Engineer", "ML Engineer"]
    )

    resume = st.file_uploader(
        "Upload Resume (PDF / DOCX / TXT)",
        type=["pdf", "docx", "txt"]
    )

    if st.button("Run Resume Screening"):
        if not resume:
            st.error("Please upload a resume.")
        else:
            resume_text = extract_text(resume)

            candidate_id = upsert_candidate("Unknown", role=role)
            session_id = create_session(candidate_id)

            result = level1_screen(resume_text)

            save_round_result(
                session_id=session_id,
                round_no=1,
                owner="Level 1 Screening",
                question=f"Resume Screening for {role}",
                answer=resume_text,
                raw_score=result["score"],
                score=result["score"],
                passed=result["pass"],
                threshold=60.0,
                features=result
            )

            st.session_state.session_id = session_id
            st.session_state.resume_text = resume_text
            st.session_state.stage1_pass = result["pass"]

            if result["pass"]:
                st.success("✅ PASSED Resume Screening")
                st.session_state.stage = 2
            else:
                st.error("❌ FAILED Resume Screening")

            st.write("Score:", result["score"])
            st.write("Reason:", result["reason"])

# --------------------------------------------------
# Stage 2 — Technical Evaluation
# --------------------------------------------------

elif st.session_state.stage == 2:
    st.header("🧪 Level 2 — Technical Evaluation")

    st.write("Answer the technical competency checks:")

    q1 = st.checkbox("Understands APIs & HTTP")
    q2 = st.checkbox("Understands Databases & Indexing")
    q3 = st.checkbox("Understands Scalability & Caching")

    answers = {
        "q1": {"correct": q1},
        "q2": {"correct": q2},
        "q3": {"correct": q3},
    }

    if st.button("Run Technical Evaluation"):
        result = level2_technical(answers)

        save_round_result(
            session_id=st.session_state.session_id,
            round_no=2,
            owner="Level 2 Technical",
            question="Technical Evaluation",
            answer=str(answers),
            raw_score=result["prob_pass"] * 100,
            score=result["prob_pass"] * 100,
            passed=result["pass"],
            threshold=50.0,
            metrics=result
        )

        st.session_state.stage2_pass = result["pass"]

        if result["pass"]:
            st.success("✅ PASSED Technical Evaluation")
            st.session_state.stage = 3
        else:
            st.error("❌ FAILED Technical Evaluation")

        st.write("Pass Probability:", result["prob_pass"])

# --------------------------------------------------
# Stage 3 — Scenario + Final Verdict
# --------------------------------------------------

elif st.session_state.stage == 3:
    st.header("🧠 Level 3 — Scenario Reasoning")

    scenario = st.text_area(
        "Describe how you would handle a production outage",
        height=200
    )

    if st.button("Run Scenario Evaluation"):
        if not scenario.strip():
            st.error("Scenario answer is required.")
        else:
            result = level3_scenario(scenario)

            save_round_result(
                session_id=st.session_state.session_id,
                round_no=3,
                owner="Level 3 Scenario",
                question="Production Incident Handling",
                answer=scenario,
                raw_score=result["score"],
                score=result["score"],
                passed=result["pass"],
                threshold=75.0,
                metrics=result
            )

            final_decision = "HIRE" if result["pass"] else "HOLD"

            complete_session(
                session_id=st.session_state.session_id,
                final_score=result["score"],
                final_decision=final_decision
            )

            st.markdown("---")
            st.subheader("🏁 Final Verdict")

            if result["pass"]:
                st.success(f"✅ FINAL DECISION: {final_decision}")
            else:
                st.error(f"⚠️ FINAL DECISION: {final_decision}")

            st.write("Score:", result["score"])
            st.write("Reason:", result["reason"])
            st.write("Session ID:", st.session_state.session_id)

            with st.expander("📄 View Resume Text"):
                st.text(st.session_state.resume_text)
