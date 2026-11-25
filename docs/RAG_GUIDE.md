# RAG in this project – explained simply

## 1. What problem does RAG solve?
An LLM only knows what it was trained on. It does not know that *Tirol IoT Solutions* was sued last month.
**RAG (Retrieval-Augmented Generation)** = first **find** the relevant text, then give it to the LLM and ask it
to answer **only from that text**.

## 2. The four steps here
| Step | File | What happens |
|---|---|---|
| Load + clean | `web.py` | Read HTML, remove menus, scripts, footers |
| Chunk | `rag.py` | One chunk per paragraph, id like `C008#5` |
| Retrieve | `rag.py` | BM25 ranks chunks for a question, inside one company |
| Generate | `llm.py` | Prompt = mandate + company + evidence; LLM must cite ids |

## 3. Why BM25 and not embeddings?
- BM25 scores a chunk higher if it contains rare query words often, adjusted for chunk length.
- Fully offline, no cost, explainable ("it matched *lawsuit*").
- Weakness: no meaning. "suing" ≠ "lawsuit" → fixed with a small synonym list.
- Next step: embeddings (meaning), ideally **hybrid** (BM25 + embeddings).

## 4. How quality is measured
- **hit@1**: correct passage ranked first. **hit@3**: correct passage in top 3.
- **MRR**: 1/rank of the first correct passage, averaged (1.0 = always first).
- Baseline 67% hit@1 → error analysis → stemming + synonyms → 83% hit@1, MRR 0.88.

## 5. Guardrails against hallucination
- The LLM sees only retrieved evidence and must return JSON with `citations`.
- Citations must be ids that were actually given → otherwise the answer is **rejected** and the rule result stays.
- API errors never break the pipeline (fallback to rules).

## 6. Interview questions to be ready for
| Question | Short answer |
|---|---|
| Why chunk by paragraph? | Small, one topic each, easy to cite; websites are short |
| How do you stop hallucinations? | Evidence-only prompt + mandatory, validated citations + fallback |
| How do you know retrieval works? | Labelled question set, hit@k and MRR, error analysis |
| What would you improve? | Hybrid retrieval with embeddings, eval set for LLM answers, caching, crawl live sites politely (robots.txt, rate limit) |
| Why only "maybe" cases to the LLM? | Cost and speed: clear cases are decided by rules; LLM only where judgement is needed |
