"""Optional second opinion from an LLM for 'maybe' cases.

Uses the Anthropic Messages REST API with plain `requests` (JSON in, JSON out).
If no API key is set, or the call fails, the rule result is kept - the pipeline never breaks.
"""
import json
import os
import re

import requests

from .models import Company, Result, LABELS

API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = os.getenv("SCREENER_MODEL", "claude-haiku-5-5")

PROMPT = """You are an M&A analyst screening acquisition targets for a buyer.

Buyer mandate (JSON):
{mandate}

Company (JSON):
{company}

A rule engine labelled this company "{rule_label}" because: {rule_rationale}

Decide the final label. Rules:
- "fit": meets the mandate and has no serious risk.
- "maybe": worth a closer look by the deal team (borderline numbers or a risk that may be manageable).
- "no_fit": clear miss or a serious risk (e.g. active litigation over core IP, sanctions exposure).

Answer with JSON only, no other text:
{{"label": "fit|maybe|no_fit", "rationale": "max 2 sentences", "confidence": 0.0-1.0}}"""


def parse_llm_json(text: str) -> dict | None:
    """Extract and validate the first JSON object in a model reply."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    if data.get("label") not in LABELS or not isinstance(data.get("rationale"), str):
        return None
    return data


def ask_llm(company: Company, mandate: dict, rule: Result, api_key: str, model: str = DEFAULT_MODEL,
            timeout: int = 30) -> dict | None:
    prompt = PROMPT.format(
        mandate=json.dumps(mandate, ensure_ascii=False),
        company=json.dumps(company.__dict__, ensure_ascii=False),
        rule_label=rule.label, rule_rationale=rule.rationale,
    )
    resp = requests.post(
        API_URL,
        headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={"model": model, "max_tokens": 300, "messages": [{"role": "user", "content": prompt}]},
        timeout=timeout,
    )
    resp.raise_for_status()
    text = "".join(block.get("text", "") for block in resp.json().get("content", []))
    return parse_llm_json(text)


def review_maybes(companies, results, mandate, api_key=None, ask=ask_llm) -> list[Result]:
    """Send only 'maybe' results to the LLM. `ask` is injectable so tests run without network."""
    api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return results
    by_id = {c.company_id: c for c in companies}
    for r in results:
        if r.label != "maybe":
            continue
        try:
            answer = ask(by_id[r.company_id], mandate, r, api_key)
        except Exception as e:  # network/HTTP errors: keep rule result
            r.rationale += f" [LLM review skipped: {type(e).__name__}]"
            continue
        if answer:
            r.label = answer["label"]
            r.rationale = f"{r.rationale} LLM review ({answer.get('confidence', 'n/a')}): {answer['rationale']}"
            r.source = "rules+llm"
    return results
