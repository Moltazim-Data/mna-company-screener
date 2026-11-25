"""Retrieval (the "R" in RAG) over company websites.

1. Split each website into small chunks (one paragraph each), keeping the section name.
2. Index all chunks with BM25, a classic keyword ranking method (no API, no GPU, fully offline).
3. For each screening question, retrieve the top-k chunks of one company.
4. Those chunks are passed to the LLM as evidence, with ids it must cite.

BM25 matches words, not meaning, so screening questions are expanded with
synonyms ("litigation" -> "lawsuit", "court", ...). An embedding model could
replace BM25 later without changing the rest of the pipeline.
"""
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .web import html_to_blocks, load_html

STOPWORDS = set("""a an the and or of to in on for with by is are was were be been it its this that as at from
our we you your has have had not no any all can will into than then there their they them which who what when
does do did about such per""".split())

# Screening questions a deal team asks about every target
RISK_QUESTIONS = {
    "legal": "Is the company involved in litigation, lawsuits or court cases?",
    "sanctions": "Is there any sanctions, ownership or compliance risk?",
    "restructuring": "Has the company gone through restructuring, losses or insolvency, and is it resolved?",
    "concentration": "Does the company depend on one large customer?",
}

SYNONYMS = {
    "litigation": ["lawsuit", "court", "legal", "claim", "dispute", "patent", "infringement"],
    "lawsuits": ["lawsuit"],
    "sanctions": ["sanction", "authorities", "review", "frozen", "shareholder"],
    "compliance": ["authorities", "review"],
    "ownership": ["owned", "shareholder", "shareholders"],
    "restructuring": ["restructuring", "sold", "refinanced", "profitable"],
    "losses": ["loss", "break-even", "losses"],
    "insolvency": ["insolvent", "bankruptcy"],
    "depend": ["dependency", "accounts", "single", "largest"],
    "customer": ["customer", "customers", "revenue"],
    "suing": ["lawsuit", "court", "claim"],
    "sue": ["lawsuit", "court", "claim"],
    "profitable": ["profit", "break-even", "profitable"],
    "owns": ["owned", "shareholder"],
    "sell": ["product", "products", "offer"],
    "growing": ["growth", "revenue"],
    "blocked": ["frozen"],
}


def stem(w: str) -> str:
    """Very light stemmer: owns/owned/owning -> own, customers -> customer."""
    for suffix in ("ing", "ed", "es", "s"):
        if len(w) > len(suffix) + 2 and w.endswith(suffix) and not w.endswith("ss"):
            return w[: -len(suffix)]
    return w


def tokenize(text: str) -> list[str]:
    words = re.findall(r"[a-zäöüß0-9\-%]+", text.lower())
    return [stem(w) for w in words if w not in STOPWORDS]


def expand(query: str) -> list[str]:
    toks = tokenize(query)
    extra = [s for t in re.findall(r"[a-z\-]+", query.lower()) for s in SYNONYMS.get(t, [])]
    return toks + tokenize(" ".join(extra))


@dataclass
class Chunk:
    chunk_id: str          # e.g. "C008#5"
    company_id: str
    section: str
    text: str


def chunk_website(company_id: str, html: str) -> list[Chunk]:
    return [Chunk(f"{company_id}#{i}", company_id, section, text)
            for i, (section, text) in enumerate(html_to_blocks(html), start=1)]


class BM25Index:
    """Okapi BM25 over chunks. k1 controls term saturation, b controls length normalisation."""

    def __init__(self, chunks: list[Chunk], k1: float = 1.5, b: float = 0.75):
        self.chunks, self.k1, self.b = chunks, k1, b
        self.tokens = [tokenize(c.section + " " + c.text) for c in chunks]
        self.tf = [Counter(t) for t in self.tokens]
        self.avgdl = sum(len(t) for t in self.tokens) / max(len(self.tokens), 1)
        df = Counter(w for t in self.tokens for w in set(t))
        n = len(chunks)
        self.idf = {w: math.log(1 + (n - d + 0.5) / (d + 0.5)) for w, d in df.items()}

    def score(self, query_tokens: list[str], i: int) -> float:
        tf, dl, s = self.tf[i], len(self.tokens[i]), 0.0
        for w in set(query_tokens):
            if w in tf:
                f = tf[w]
                s += self.idf.get(w, 0) * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
        return s

    def search(self, query: str, company_id: str | None = None, k: int = 3) -> list[tuple[Chunk, float]]:
        q = expand(query)
        hits = [(c, self.score(q, i)) for i, c in enumerate(self.chunks)
                if company_id is None or c.company_id == company_id]
        hits = [h for h in hits if h[1] > 0]
        return sorted(hits, key=lambda h: -h[1])[:k]


def build_index(website_dir: str | Path, company_ids=None) -> BM25Index:
    chunks = []
    for path in sorted(Path(website_dir).glob("*.html")):
        cid = path.stem
        if company_ids is None or cid in company_ids:
            chunks += chunk_website(cid, load_html(path))
    return BM25Index(chunks)


def evidence_for(index: BM25Index, company_id: str, k: int = 2) -> list[dict]:
    """Top chunks per risk question for one company, ready to put into an LLM prompt."""
    out, seen = [], set()
    for topic, question in RISK_QUESTIONS.items():
        for chunk, score in index.search(question, company_id, k):
            if chunk.chunk_id not in seen:
                seen.add(chunk.chunk_id)
                out.append({"id": chunk.chunk_id, "topic": topic, "section": chunk.section,
                            "text": chunk.text, "score": round(score, 2)})
    return out
