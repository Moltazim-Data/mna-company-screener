"""Measure retrieval quality: is the right chunk in the top results?

hit@k = share of questions where a correct chunk is among the first k results
MRR   = mean reciprocal rank (1 if the correct chunk is first, 0.5 if second, ...)
"""
import json
from pathlib import Path


def load_rag_eval(path: str | Path) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))["items"]


def evaluate_retrieval(index, items: list[dict], k: int = 3) -> dict:
    rows, hits1, hitsk, rr = [], 0, 0, 0.0
    for it in items:
        results = index.search(it["question"], it["company_id"], k)
        rank = next((i for i, (c, _) in enumerate(results, start=1)
                     if it["expected"].lower() in c.text.lower()), None)
        hits1 += rank == 1
        hitsk += rank is not None
        rr += 1 / rank if rank else 0
        rows.append({**it, "rank": rank, "top_chunk": results[0][0].chunk_id if results else None})
    n = len(items) or 1
    return {"n": len(items), "k": k, "hit@1": hits1 / n, f"hit@{k}": hitsk / n, "mrr": rr / n, "items": rows}


def format_rag_report(ev: dict) -> str:
    k = ev["k"]
    lines = [f"Retrieval evaluation on {ev['n']} questions",
             f"hit@1: {ev['hit@1']:.0%}   hit@{k}: {ev[f'hit@{k}']:.0%}   MRR: {ev['mrr']:.2f}"]
    misses = [r for r in ev["items"] if r["rank"] != 1]
    if misses:
        lines.append("Not ranked first:")
        lines += [f"  {r['company_id']}: '{r['question']}' -> rank {r['rank']}" for r in misses]
    return "\n".join(lines)
