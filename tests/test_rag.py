from pathlib import Path

import pytest

from screener.evaluate import evaluate
from screener.evaluate_rag import evaluate_retrieval, load_rag_eval
from screener.io import load_companies, load_labels, load_mandate
from screener.llm import attach_evidence, parse_llm_json, review_maybes
from screener.rag import BM25Index, build_index, chunk_website, tokenize
from screener.rules import screen_all
from screener.web import html_to_blocks

ROOT = Path(__file__).resolve().parents[1]

HTML = """<html><head><script>var tracking=1;</script><style>p{}</style></head><body>
<nav>Home | Contact</nav><h2>About</h2><p>We build   sensors.</p><h2>News</h2><p>A lawsuit was filed.</p>
<footer>Imprint</footer></body></html>"""


@pytest.fixture(scope="module")
def index():
    return build_index(ROOT / "data/websites")


def test_html_cleaning_removes_menus_scripts_and_footer():
    blocks = html_to_blocks(HTML)
    assert blocks == [("About", "We build sensors."), ("News", "A lawsuit was filed.")]


def test_chunks_have_stable_ids():
    chunks = chunk_website("X1", HTML)
    assert [c.chunk_id for c in chunks] == ["X1#1", "X1#2"]
    assert chunks[1].section == "News"


def test_light_stemming_matches_word_forms():
    assert tokenize("owns")[0] == tokenize("owned")[0] == "own"


def test_search_is_limited_to_one_company(index):
    hits = index.search("lawsuit court", "C008", k=5)
    assert hits and all(c.company_id == "C008" for c, _ in hits)
    assert "lawsuit" in hits[0][0].text


def test_synonym_expansion_finds_lawsuit_for_litigation():
    idx = BM25Index(chunk_website("X1", HTML))
    hits = idx.search("Is the company involved in litigation?", "X1", k=1)
    assert "lawsuit" in hits[0][0].text


def test_retrieval_quality_on_eval_set(index):
    ev = evaluate_retrieval(index, load_rag_eval(ROOT / "data/rag_eval.json"), k=3)
    assert ev["hit@1"] >= 0.80
    assert ev["hit@3"] >= 0.90


def test_citations_must_come_from_evidence():
    ok = '{"label": "no_fit", "rationale": "Active lawsuit.", "citations": ["C008#5"]}'
    invented = '{"label": "no_fit", "rationale": "Active lawsuit.", "citations": ["C999#1"]}'
    missing = '{"label": "no_fit", "rationale": "Active lawsuit."}'
    allowed = {"C008#5", "C008#6"}
    assert parse_llm_json(ok, allowed)["citations"] == ["C008#5"]
    assert parse_llm_json(invented, allowed) is None
    assert parse_llm_json(missing, allowed) is None


def test_evidence_is_attached_only_to_maybes(index):
    companies = load_companies(ROOT / "data/companies.csv")
    results = attach_evidence(screen_all(companies, load_mandate(ROOT / "data/mandate.json")), index)
    assert all(r.evidence_items for r in results if r.label == "maybe")
    assert not any(r.evidence_items for r in results if r.label != "maybe")
    c008 = next(r for r in results if r.company_id == "C008")
    assert "lawsuit" in c008.evidence


def test_grounded_llm_review_reaches_full_accuracy(index):
    """A fake LLM that decides ONLY from the retrieved evidence fixes the 3 rule-only errors."""
    companies = load_companies(ROOT / "data/companies.csv")
    mandate = load_mandate(ROOT / "data/mandate.json")
    results = attach_evidence(screen_all(companies, mandate), index)

    def evidence_only_llm(company, mandate, rule, api_key, evidence=None):
        text = " ".join(e["text"].lower() for e in evidence or [])
        cite = [evidence[0]["id"]] if evidence else []
        if "lawsuit" in text or "sanctions review" in text:
            return {"label": "no_fit", "rationale": "Serious legal risk in evidence.", "citations": cite}
        if "completed its restructuring" in text and "profitable" in text:
            return {"label": "fit", "rationale": "Restructuring finished, profitable.", "citations": cite}
        return {"label": "maybe", "rationale": "Needs deal-team review.", "citations": cite}

    results = review_maybes(companies, results, mandate, api_key="test", ask=evidence_only_llm)
    assert evaluate(results, load_labels(ROOT / "data/eval_labels.csv"))["accuracy"] == 1.0
    assert all("sources:" in r.rationale for r in results if r.source == "rules+llm")
