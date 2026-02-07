# Main.py
# FastAPI entry point for resume + role based screening (Level 1)

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from models.Level1screening import level1_screen
from db import upsert_candidate, create_session, save_round_result, complete_session

app = FastAPI(
    title="Multi-Round Interview Agent",
    description="Resume-based screening system",
    version="1.0"
)


@app.post("/screen_resume")
async def screen_resume(
    resume: UploadFile = File(...),
    role: str = Form(...)
):
    # ----------------------------
    # Read resume text
    # ----------------------------
    try:
        content = await resume.read()
        resume_text = content.decode("utf-8", errors="ignore")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid resume file")

    # ----------------------------
    # Create candidate + session
    # ----------------------------
    candidate_id = upsert_candidate(
        full_name="Unknown",
        role=role
    )
    session_id = create_session(candidate_id)

    # ----------------------------
    # LEVEL 1 — SCREENING
    # ----------------------------
    result = level1_screen(resume_text)

    save_round_result(
        session_id=session_id,
        round_no=1,
        owner="Screening Engine",
        question=f"Resume screening for role: {role}",
        answer=resume_text,
        raw_score=result.get("score", 0.0),
        score=result.get("score", 0.0),
        passed=result.get("pass", False),
        threshold=60.0,
        features=result
    )

    final_decision = "PASS" if result.get("pass") else "REJECT"

    complete_session(
        session_id=session_id,
        final_score=result.get("score", 0.0),
        final_decision=final_decision
    )

    return {
        "role": role,
        "screening_pass": result.get("pass"),
        "score": result.get("score"),
        "reason": result.get("reason"),
        "session_id": session_id
    }


@app.get("/")
def root():
    return {"status": "ok", "message": "Resume screening service running"}
