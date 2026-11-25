"""Compare screener labels with analyst labels: accuracy, confusion matrix, error list."""
from .models import LABELS


def evaluate(results, gold: dict[str, str]) -> dict:
    pairs = [(gold[r.company_id], r.label, r) for r in results if r.company_id in gold]
    if not pairs:
        return {"n": 0, "accuracy": None, "matrix": {}, "errors": [], "safe_rate": None}
    matrix = {g: {p: 0 for p in LABELS} for g in LABELS}
    errors = []
    for g, p, r in pairs:
        matrix[g][p] += 1
        if g != p:
            errors.append({"company_id": r.company_id, "name": r.name, "analyst": g, "screener": p})
    correct = sum(matrix[l][l] for l in LABELS)
    # "dangerous" error = analyst says no_fit but screener says fit (deal team wastes time / misses risk)
    dangerous = matrix["no_fit"]["fit"]
    return {
        "n": len(pairs),
        "accuracy": correct / len(pairs),
        "matrix": matrix,
        "errors": errors,
        "dangerous_errors": dangerous,
    }


def format_report(ev: dict) -> str:
    if not ev["n"]:
        return "No labelled companies to evaluate."
    lines = [f"Evaluated on {ev['n']} analyst-labelled companies",
             f"Accuracy: {ev['accuracy']:.1%}",
             f"Dangerous errors (analyst no_fit -> screener fit): {ev['dangerous_errors']}",
             "", "Confusion matrix (rows = analyst, cols = screener):",
             "          " + "".join(f"{l:>8}" for l in LABELS)]
    for g in LABELS:
        lines.append(f"{g:>8}  " + "".join(f"{ev['matrix'][g][p]:>8}" for p in LABELS))
    if ev["errors"]:
        lines += ["", "Disagreements:"] + [f"  {e['company_id']} {e['name']}: analyst={e['analyst']}, screener={e['screener']}"
                                           for e in ev["errors"]]
    return "\n".join(lines)
