"""Deterministic first-pass screening against a buyer mandate.

Logic
-----
1. Hard criteria (country, sector, revenue range, excluded owners): any miss -> no_fit.
2. Soft criteria (EBITDA margin, growth, headcount): 0 misses -> fit, 1 miss -> maybe, 2+ misses -> no_fit.
   A soft miss within the borderline tolerance counts as "borderline" and caps the result at maybe.
3. Red-flag keywords in the description (litigation, sanctions, ...) -> at least maybe, flagged for human/LLM review.
Every decision comes with a plain-English rationale.
"""
from .models import Company, Result


def _within(value: float, limit: float, tol: float, higher_is_better: bool) -> bool:
    """True if a missed threshold is still within tolerance (e.g. 9.5% margin vs 10% limit)."""
    if higher_is_better:
        return value >= limit * (1 - tol)
    return value <= limit * (1 + tol)


def screen_company(c: Company, mandate: dict) -> Result:
    hard = mandate["hard_criteria"]
    soft = mandate["soft_criteria"]
    tol = mandate.get("borderline_tolerance", 0.10)
    reasons, checks = [], {}

    # --- hard criteria ---
    hard_fails = []
    if c.country not in hard["countries"]:
        hard_fails.append(f"country {c.country} outside {'/'.join(hard['countries'])}")
    if c.sector not in hard["sectors"]:
        hard_fails.append(f"sector '{c.sector}' not in target sectors")
    lo, hi = hard["revenue_eur_m"]["min"], hard["revenue_eur_m"]["max"]
    if not lo <= c.revenue_eur_m <= hi:
        hard_fails.append(f"revenue EUR {c.revenue_eur_m:.1f}m outside EUR {lo}-{hi}m")
    if c.owner_type in hard.get("excluded_owners", []):
        hard_fails.append(f"owner type '{c.owner_type}' excluded")
    checks["hard_fails"] = hard_fails

    # --- soft criteria ---
    soft_fails, borderline = [], []
    tests = [
        ("EBITDA margin", c.ebitda_margin, soft["min_ebitda_margin"], True, "{:.0%}"),
        ("revenue growth", c.revenue_growth, soft["min_revenue_growth"], True, "{:.0%}"),
        ("employees", c.employees, soft["max_employees"], False, "{:.0f}"),
    ]
    for name, val, limit, hib, fmt in tests:
        ok = val >= limit if hib else val <= limit
        if ok:
            continue
        msg = f"{name} {fmt.format(val)} vs {'min' if hib else 'max'} {fmt.format(limit)}"
        (borderline if _within(val, limit, tol, hib) else soft_fails).append(msg)
    checks["soft_fails"], checks["borderline"] = soft_fails, borderline

    # --- red flags ---
    text = c.description.lower()
    flags = [f for f in mandate.get("red_flags", []) if f in text]
    checks["red_flags"] = flags

    # --- decision ---
    if hard_fails:
        label = "no_fit"
        reasons.append("Fails hard criteria: " + "; ".join(hard_fails) + ".")
    else:
        misses = len(soft_fails) + len(borderline)
        if len(soft_fails) >= 2 or misses >= 3:
            label = "no_fit"
        elif misses == 0:
            label = "fit"
        else:
            label = "maybe"
        if soft_fails:
            reasons.append("Misses: " + "; ".join(soft_fails) + ".")
        if borderline:
            reasons.append("Borderline: " + "; ".join(borderline) + ".")
        if label == "fit":
            reasons.append(f"Meets all criteria: {c.sector}, {c.country}, EUR {c.revenue_eur_m:.1f}m revenue, "
                           f"{c.ebitda_margin:.0%} EBITDA margin, {c.revenue_growth:.0%} growth.")
        if flags and label == "fit":
            label = "maybe"
        if flags:
            reasons.append("Red flag in description: " + ", ".join(flags) + " -> needs review.")

    score = 0 if hard_fails else max(0, 100 - 30 * len(soft_fails) - 15 * len(borderline) - 20 * len(flags))
    return Result(c.company_id, c.name, label, " ".join(reasons), "rules", label, score, checks=checks)


def screen_all(companies, mandate) -> list[Result]:
    return [screen_company(c, mandate) for c in companies]
