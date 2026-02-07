# db.py
# SQLite persistence for Multi-Round Interview Agent
# Stores: candidates, interview sessions, per-round results, and final decisions

import sqlite3
import json
import uuid
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple

DB_PATH = Path(__file__).resolve().parent / "interviews.db"


# --------------------------
# Utilities
# --------------------------

def _utc_now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


@contextmanager
def get_conn(db_path: Path = DB_PATH):
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# --------------------------
# Schema initialization
# --------------------------

def init_db(db_path: Path = DB_PATH) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with get_conn(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS candidates (
                candidate_id TEXT PRIMARY KEY,
                full_name    TEXT,
                email        TEXT,
                phone        TEXT,
                role         TEXT,
                created_at   TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                session_id     TEXT PRIMARY KEY,
                candidate_id   TEXT NOT NULL,
                status         TEXT NOT NULL, -- IN_PROGRESS / COMPLETED
                final_score    REAL,
                final_decision TEXT,          -- HIRE / HOLD / REJECT
                created_at     TEXT NOT NULL,
                completed_at   TEXT,
                FOREIGN KEY(candidate_id)
                    REFERENCES candidates(candidate_id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS round_results (
                result_id        TEXT PRIMARY KEY,
                session_id       TEXT NOT NULL,
                round_no         INTEGER NOT NULL, -- 1,2,3
                owner            TEXT,
                question_id      TEXT,
                question         TEXT,
                answer           TEXT,
                raw_score        REAL,
                score            REAL,
                passed           INTEGER NOT NULL, -- 0/1
                threshold        REAL,
                violations_json TEXT,
                metrics_json    TEXT,
                features_json   TEXT,
                entropy_value   REAL,
                created_at      TEXT NOT NULL,
                FOREIGN KEY(session_id)
                    REFERENCES sessions(session_id)
                    ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_sessions_candidate
                ON sessions(candidate_id);

            CREATE INDEX IF NOT EXISTS idx_round_results_session_round
                ON round_results(session_id, round_no);
            """
        )


# --------------------------
# Candidate + session
# --------------------------

def upsert_candidate(
    full_name: str,
    email: str = "",
    phone: str = "",
    role: str = "Backend Engineer",
    candidate_id: Optional[str] = None,
) -> str:
    init_db()
    cid = candidate_id or _new_id("cand")

    with get_conn() as conn:
        existing = conn.execute(
            "SELECT candidate_id FROM candidates WHERE candidate_id=?",
            (cid,),
        ).fetchone()

        if existing:
            conn.execute(
                """
                UPDATE candidates
                SET full_name=?, email=?, phone=?, role=?
                WHERE candidate_id=?
                """,
                (full_name, email, phone, role, cid),
            )
        else:
            conn.execute(
                """
                INSERT INTO candidates(
                    candidate_id, full_name, email, phone, role, created_at
                )
                VALUES(?,?,?,?,?,?)
                """,
                (cid, full_name, email, phone, role, _utc_now()),
            )
    return cid


def create_session(candidate_id: str) -> str:
    init_db()
    sid = _new_id("sess")
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO sessions(
                session_id, candidate_id, status, created_at
            )
            VALUES(?,?,?,?)
            """,
            (sid, candidate_id, "IN_PROGRESS", _utc_now()),
        )
    return sid


# --------------------------
# Round results
# --------------------------

def save_round_result(
    session_id: str,
    round_no: int,
    owner: str,
    question: str,
    answer: str,
    raw_score: float,
    score: float,
    passed: bool,
    threshold: float,
    question_id: Optional[str] = None,
    violations: Optional[List[str]] = None,
    metrics: Optional[Dict[str, Any]] = None,
    features: Optional[Dict[str, Any]] = None,
    entropy_value: Optional[float] = None,
) -> str:
    init_db()
    rid = _new_id("res")

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO round_results(
                result_id, session_id, round_no, owner,
                question_id, question, answer,
                raw_score, score, passed, threshold,
                violations_json, metrics_json, features_json,
                entropy_value, created_at
            )
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                rid,
                session_id,
                int(round_no),
                owner,
                question_id,
                question,
                answer,
                float(raw_score),
                float(score),
                1 if passed else 0,
                float(threshold),
                json.dumps(violations or [], ensure_ascii=False),
                json.dumps(metrics or {}, ensure_ascii=False),
                json.dumps(features or {}, ensure_ascii=False),
                float(entropy_value) if entropy_value is not None else None,
                _utc_now(),
            ),
        )
    return rid


def get_round_results(session_id: str) -> List[Dict[str, Any]]:
    init_db()
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM round_results
            WHERE session_id=?
            ORDER BY round_no ASC, created_at ASC
            """,
            (session_id,),
        ).fetchall()

    out: List[Dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                "result_id": r["result_id"],
                "session_id": r["session_id"],
                "round_no": r["round_no"],
                "owner": r["owner"],
                "question_id": r["question_id"],
                "question": r["question"],
                "answer": r["answer"],
                "raw_score": r["raw_score"],
                "score": r["score"],
                "passed": bool(r["passed"]),
                "threshold": r["threshold"],
                "violations": json.loads(r["violations_json"] or "[]"),
                "metrics": json.loads(r["metrics_json"] or "{}"),
                "features": json.loads(r["features_json"] or "{}"),
                "entropy_value": r["entropy_value"],
                "created_at": r["created_at"],
            }
        )
    return out


# --------------------------
# Final decision
# --------------------------

def complete_session(
    session_id: str,
    final_score: float,
    final_decision: str,  # HIRE / HOLD / REJECT
) -> None:
    init_db()
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE sessions
            SET status=?,
                final_score=?,
                final_decision=?,
                completed_at=?
            WHERE session_id=?
            """,
            (
                "COMPLETED",
                float(final_score),
                final_decision,
                _utc_now(),
                session_id,
            ),
        )


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    init_db()
    with get_conn() as conn:
        s = conn.execute(
            "SELECT * FROM sessions WHERE session_id=?",
            (session_id,),
        ).fetchone()

    if not s:
        return None

    return {
        "session_id": s["session_id"],
        "candidate_id": s["candidate_id"],
        "status": s["status"],
        "final_score": s["final_score"],
        "final_decision": s["final_decision"],
        "created_at": s["created_at"],
        "completed_at": s["completed_at"],
    }


def list_sessions(
    candidate_id: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    init_db()
    q = "SELECT * FROM sessions "
    params: Tuple[Any, ...] = ()

    if candidate_id:
        q += "WHERE candidate_id=? "
        params = (candidate_id,)

    q += "ORDER BY created_at DESC LIMIT ?"
    params = params + (int(limit),)

    with get_conn() as conn:
        rows = conn.execute(q, params).fetchall()

    return [
        {
            "session_id": r["session_id"],
            "candidate_id": r["candidate_id"],
            "status": r["status"],
            "final_score": r["final_score"],
            "final_decision": r["final_decision"],
            "created_at": r["created_at"],
            "completed_at": r["completed_at"],
        }
        for r in rows
    ]
