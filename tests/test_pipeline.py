from pathlib import Path

import pytest
from openpyxl import load_workbook
from pptx import Presentation

from screener.__main__ import main
from screener.evaluate import evaluate
from screener.io import load_companies, load_labels, load_mandate
from screener.llm import parse_llm_json, review_maybes
from screener.rules import screen_all

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def data():
    companies = load_companies(ROOT / "data/companies.csv")
    mandate = load_mandate(ROOT / "data/mandate.json")
    return companies, mandate, load_labels(ROOT / "data/eval_labels.csv")


def test_rules_baseline_quality(data):
    companies, mandate, gold = data
    ev = evaluate(screen_all(companies, mandate), gold)
    assert ev["accuracy"] >= 0.85
    assert ev["dangerous_errors"] == 0   # never call a no_fit company a fit


def test_parse_llm_json_handles_extra_text():
    assert parse_llm_json('Sure! {"label": "no_fit", "rationale": "Sanctions risk.", "confidence": 0.9}')["label"] == "no_fit"
    assert parse_llm_json('{"label": "great", "rationale": "x"}') is None
    assert parse_llm_json("no json here") is None


def test_llm_review_only_touches_maybes(data):
    companies, mandate, gold = data
    results = screen_all(companies, mandate)
    before = {r.company_id: r.label for r in results}
    calls = []

    def fake_ask(company, mandate, rule, api_key):
        calls.append(company.company_id)
        text = company.description.lower()
        if "sanctions" in text or "litigation" in text:
            return {"label": "no_fit", "rationale": "Serious legal risk.", "confidence": 0.8}
        if "restructuring completed" in text:
            return {"label": "fit", "rationale": "Restructuring is finished.", "confidence": 0.7}
        return {"label": "maybe", "rationale": "Borderline numbers.", "confidence": 0.6}

    results = review_maybes(companies, results, mandate, api_key="test", ask=fake_ask)
    assert set(calls) == {cid for cid, lab in before.items() if lab == "maybe"}
    assert all(r.label == before[r.company_id] for r in results if before[r.company_id] != "maybe")
    assert evaluate(results, gold)["accuracy"] == 1.0


def test_llm_errors_keep_rule_result(data):
    companies, mandate, _ = data
    results = screen_all(companies, mandate)

    def broken(*a, **k):
        raise TimeoutError("API down")

    results = review_maybes(companies, results, mandate, api_key="test", ask=broken)
    assert any("LLM review skipped" in r.rationale for r in results)


def test_cli_writes_all_outputs(tmp_path):
    assert main(["--companies", str(ROOT / "data/companies.csv"), "--mandate", str(ROOT / "data/mandate.json"),
                 "--labels", str(ROOT / "data/eval_labels.csv"), "--out", str(tmp_path)]) == 0
    for name in ["screening_results.csv", "screening_results.xlsx", "screening_summary.pptx", "evaluation.json"]:
        assert (tmp_path / name).exists()
    wb = load_workbook(tmp_path / "screening_results.xlsx")
    assert wb.sheetnames == ["Summary", "Screening", "Mandate"]
    assert wb["Screening"].max_row == 31
    assert len(Presentation(tmp_path / "screening_summary.pptx").slides) == 1


def test_bad_input_is_rejected(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("company_id,name\nX,Only two columns\n")
    with pytest.raises(ValueError, match="Missing columns"):
        load_companies(bad)
