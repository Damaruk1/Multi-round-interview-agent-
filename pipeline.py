# pipeline.py
# Orchestrates the multi-round interview process:
# Level 1 -> Level 2 -> Level 3
# Persists all intermediate and final results to SQLite via db.py

from typing import Dict, Any

# IMPORTANT: imports match your current filenames exactly
from models.Level1screening import level1_screen
from models.Level2technical import level2_technical
from models.Level3scenario import level3_scenario

from db import (
    upsert_candidate,
    create_session,
    save_round_result,
    complete_session,
)


def evaluate_candidate(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    payload structure:
    {
        "full_name": str,
        "email": str,
        "phone": str,
        "role": str,

        "resume_text": str,
        "technical_answers": dict,
        "scenario_answer": str
    }
    """

    # --------------------------
    # Candidate + session setup
    # --------------------------
    candidate_id = upsert_candidate(
        full_name=payload.get("full_name", "Unknown"),
        email=payload.get("email", ""),
        phone=payload.get("phone", ""),
        role=payload.get("role", "Backend Engineer"),
    )

    session_id = create_session(candidate_id)

    # ==================================================
    # LEVEL 1 — SCREENING
    # ==================================================
    resume_text = payload.get("resume_text", "")
    l1 = level1_screen(resume_text)

    save_round_result(
        session_id=session_id,
        round_no=1,
        owner="Interviewer L1",
        question="Resume Screening",
        answer=resume_text,
        raw_score=l1.get("score", 0.0),
        score=l1.get("score", 0.0),
        passed=l1.get("pass", False),
        threshold=60.0,
        features=l1,
    )

    if not l1.get("pass", False):
        complete_session(
            session_id=session_id,
            final_score=l1.get("score", 0.0),
            final_decision="REJECT",
        )
        return {
            "final_pass": False,
            "failed_at": "level1",
            "session_id": session_id,
            "level1": l1,
        }

    # ==================================================
    # LEVEL 2 — TECHNICAL
    # ==================================================
    technical_answers = payload.get("technical_answers", {})
    l2 = level2_technical(technical_answers)

    save_round_result(
        session_id=session_id,
        round_no=2,
        owner="Interviewer L2",
        question="Technical Evaluation",
        answer=str(technical_answers),
        raw_score=l2.get("prob_pass", 0.0) * 100.0,
        score=l2.get("prob_pass", 0.0) * 100.0,
        passed=l2.get("pass", False),
        threshold=50.0,
        metrics=l2,
    )

    if not l2.get("pass", False):
        complete_session(
            session_id=session_id,
            final_score=l2.get("prob_pass", 0.0) * 100.0,
            final_decision="REJECT",
        )
        return {
            "final_pass": False,
            "failed_at": "level2",
            "session_id": session_id,
            "level1": l1,
            "level2": l2,
        }

    # ==================================================
    # LEVEL 3 — SCENARIO
    # ==================================================
    scenario_answer = payload.get("scenario_answer", "")
    l3 = level3_scenario(scenario_answer)

    save_round_result(
        session_id=session_id,
        round_no=3,
        owner="Interviewer L3",
        question="Scenario-Based Reasoning",
        answer=scenario_answer,
        raw_score=l3.get("score", 0.0),
        score=l3.get("score", 0.0),
        passed=l3.get("pass", False),
        threshold=75.0,
        metrics=l3,
    )

    # ==================================================
    # FINAL DECISION
    # ==================================================
    final_decision = "HIRE" if l3.get("pass", False) else "HOLD"

    complete_session(
        session_id=session_id,
        final_score=l3.get("score", 0.0),
        final_decision=final_decision,
    )

    return {
        "final_pass": l3.get("pass", False),
        "decision": final_decision,
        "session_id": session_id,
        "level1": l1,
        "level2": l2,
        "level3": l3,
    }
