import math
import re
from collections import Counter

def level1_screen(text: str) -> dict:
    if not isinstance(text, str):
        return {"pass": False, "score": 0.0, "reason": "Invalid input"}

    tokens = re.findall(r"\w+", text.lower())
    if len(tokens) < 30:
        return {"pass": False, "score": 0.0, "reason": "Too short"}

    counts = Counter(tokens)
    total = sum(counts.values())

    entropy = -sum((c / total) * math.log(c / total) for c in counts.values())
    entropy_norm = entropy / math.log(total)

    redundancy = len(set(tokens)) / total

    score = 100 * (0.55 * min(entropy_norm, 1.0) + 0.45 * redundancy)

    return {
        "pass": score >= 60,
        "score": round(score, 2),
        "reason": "OK" if score >= 60 else "Low signal"
    }
