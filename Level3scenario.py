import re
from collections import Counter

PHASES = {
    "diagnose": ["investigate", "analyze", "identify"],
    "contain": ["rollback", "mitigate", "reduce"],
    "fix": ["fix", "resolve", "repair"],
    "prevent": ["monitor", "prevent", "automate"]
}

DIMENSIONS = {
    "risk": ["risk", "impact"],
    "cost": ["cost", "budget"],
    "time": ["downtime", "delay"],
    "reliability": ["uptime", "stability"]
}

def level3_scenario(answer: str) -> dict:
    if not isinstance(answer, str):
        return {"pass": False, "score": 0.0, "reason": "Invalid input"}

    steps = [s.strip().lower() for s in re.split(r"[.\n]+", answer) if s.strip()]
    if len(steps) < 2:
        return {"pass": False, "score": 0.0, "reason": "Too shallow"}

    phase_hits = []
    dim_hits = []

    for step in steps:
        for p, keys in PHASES.items():
            if any(k in step for k in keys):
                phase_hits.append(p)

        dims = {d for d, keys in DIMENSIONS.items() if any(k in step for k in keys)}
        if dims:
            dim_hits.append(dims)

    flow = len(set(phase_hits)) / len(PHASES)
    tradeoff = sum(len(d) for d in dim_hits) / (len(dim_hits) * len(DIMENSIONS)) if dim_hits else 0

    flat_dims = [d for ds in dim_hits for d in ds]
    dominance = max(Counter(flat_dims).values()) / len(flat_dims) if flat_dims else 1.0
    stability = 1 - dominance

    score = 100 * (0.45 * flow + 0.35 * tradeoff + 0.20 * stability)

    return {
        "pass": score >= 75,
        "score": round(score, 2),
        "reason": "OK" if score >= 75 else "Weak scenario reasoning"
    }
