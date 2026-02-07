def level2_technical(answers: dict) -> dict:
    if not isinstance(answers, dict) or not answers:
        return {"pass": False, "prob_pass": 0.0, "reason": "No answers"}

    total = 0
    correct = 0

    for v in answers.values():
        if isinstance(v, dict) and "correct" in v:
            total += 1
            if v["correct"]:
                correct += 1

    if total == 0:
        return {"pass": False, "prob_pass": 0.0, "reason": "Malformed input"}

    prob = correct / total

    return {
        "pass": prob >= 0.5,
        "prob_pass": round(prob, 3),
        "reason": "OK" if prob >= 0.5 else "Weak technical fundamentals"
    }
