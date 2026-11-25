"""CLI: python -m screener [--llm]"""
import argparse
import csv
import json
from pathlib import Path

from .evaluate import evaluate, format_report
from .export_excel import export_excel
from .export_pptx import export_pptx
from .io import load_companies, load_labels, load_mandate
from .evaluate_rag import evaluate_retrieval, format_rag_report, load_rag_eval
from .llm import attach_evidence, review_maybes
from .rag import build_index
from .rules import screen_all


def main(argv=None):
    ap = argparse.ArgumentParser(description="Screen M&A targets against a buyer mandate.")
    ap.add_argument("--companies", default="data/companies.csv")
    ap.add_argument("--mandate", default="data/mandate.json")
    ap.add_argument("--labels", default="data/eval_labels.csv", help="analyst labels for evaluation ('' to skip)")
    ap.add_argument("--out", default="output")
    ap.add_argument("--websites", default="data/websites", help="folder with company websites (HTML) for RAG ('' to skip)")
    ap.add_argument("--rag-eval", default="data/rag_eval.json", help="retrieval test set ('' to skip)")
    ap.add_argument("--llm", action="store_true", help="review 'maybe' cases with an LLM (needs ANTHROPIC_API_KEY)")
    args = ap.parse_args(argv)

    companies = load_companies(args.companies)
    mandate = load_mandate(args.mandate)
    results = screen_all(companies, mandate)
    index = build_index(args.websites) if args.websites and Path(args.websites).is_dir() else None
    if index:
        results = attach_evidence(results, index)
    if args.llm:
        results = review_maybes(companies, results, mandate)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    ev = evaluate(results, load_labels(args.labels)) if args.labels else None

    with open(out / "screening_results.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0].to_dict().keys()))
        w.writeheader()
        w.writerows(r.to_dict() for r in results)
    export_excel(out / "screening_results.xlsx", companies, results, mandate, ev)
    export_pptx(out / "screening_summary.pptx", companies, results, mandate)
    if ev:
        (out / "evaluation.json").write_text(json.dumps(ev, indent=2), encoding="utf-8")
    rag_ev = None
    if index and args.rag_eval and Path(args.rag_eval).exists():
        rag_ev = evaluate_retrieval(index, load_rag_eval(args.rag_eval))
        (out / "rag_evaluation.json").write_text(json.dumps(rag_ev, indent=2), encoding="utf-8")

    counts = {lab: sum(r.label == lab for r in results) for lab in ("fit", "maybe", "no_fit")}
    print(f"Screened {len(results)} companies -> {counts}")
    if ev:
        print(format_report(ev))
    if rag_ev:
        print()
        print(format_rag_report(rag_ev))
    print(f"Files written to {out}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
