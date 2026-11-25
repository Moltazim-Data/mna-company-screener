# M&A Company Screener

![tests](https://github.com/Moltazim-Data/mna-company-screener/actions/workflows/tests.yml/badge.svg)

Screens a long list of potential acquisition targets against a buyer mandate and sorts every company into
**fit / maybe / no_fit** with a written rationale. The results go to a formatted **Excel** file and a
one-slide **PowerPoint** summary, so the deal team gets them in a usable form.

> All companies and numbers in `data/` are **fictional sample data**.

![slide preview](docs/slide_preview.png)

## Why

In sell-side and buy-side M&A, analysts often screen hundreds of companies by hand. Most decisions follow
clear rules (country, sector, size, margin), but a few need judgement (litigation, sanctions, a finished
restructuring). This tool automates the clear part, explains each decision, sends the judgement cases to
an LLM for a second opinion and measures quality against analyst labels.

## How it works

```
companies.csv ─┐
mandate.json ──┼─> 1. Rule engine ──> 2. LLM review (only "maybe") ──> 3. Evaluation ──> Excel + PowerPoint + CSV
eval_labels ───┘     hard / soft /        optional, REST + JSON,           accuracy,
                     red-flag checks      falls back to rules on error     confusion matrix
```

1. **Rule engine** (`screener/rules.py`)
   - Hard criteria: country, sector, revenue range, excluded owner types → any miss = `no_fit`
   - Soft criteria: EBITDA margin, revenue growth, headcount → 0 misses = `fit`, 1 = `maybe`, 2+ = `no_fit`
   - Borderline values (within 10% of a threshold) are capped at `maybe`, not rejected
   - Red-flag keywords (litigation, sanctions, insolvency, …) → sent for review
2. **LLM review** (`screener/llm.py`), optional: only `maybe` cases go to the Anthropic Messages API
   through plain `requests`. The model must answer in JSON (`label`, `rationale`, `confidence`), and the
   reply is validated. If there is no API key or the call fails, the rule result stays.
3. **Evaluation** (`screener/evaluate.py`): accuracy, confusion matrix and a list of disagreements against
   30 analyst labels. "Dangerous errors" (analyst says `no_fit`, tool says `fit`) are tracked separately.
4. **Exports**: `screening_results.xlsx` (Summary, Screening, Mandate sheets, colour-coded labels, filters),
   `screening_summary.pptx` (KPI boxes + top targets in a fixed style), `screening_results.csv`.

## Results on the sample data

| Setup | Accuracy | Dangerous errors |
|---|---|---|
| Rules only | **90.0%** (27 / 30) | **0** |
| Rules + LLM review of `maybe` cases (simulated in tests) | 100% | 0 |

The 3 rule-only disagreements are judgement cases: active patent litigation, a sanctions review and a
restructuring that is already finished. These are exactly the cases the LLM step is meant for.

## Run it

```bash
pip install -r requirements.txt
python -m screener                     # rules only, writes to output/
export ANTHROPIC_API_KEY=...           # optional
python -m screener --llm               # rules + LLM review of "maybe" cases
python -m pytest -q                    # 16 tests
```

Options: `--companies`, `--mandate`, `--labels`, `--out`. Model via `SCREENER_MODEL`.

## Project structure

```
screener/
  rules.py         rule engine with rationales
  llm.py           LLM second opinion (REST + JSON, validated, safe fallback)
  evaluate.py      accuracy, confusion matrix, error list
  export_excel.py  Excel deliverable (openpyxl)
  export_pptx.py   PowerPoint slide (python-pptx)
  io.py            input loading + validation
data/              mandate, 30 fictional companies, analyst labels
tests/             16 pytest tests, LLM mocked (no network needed)
output/            sample outputs
```

## Next steps

- Read company lists directly from Excel files and data providers
- Add an evaluation set for the LLM prompt itself and track it per model version
- Small internal web app (Streamlit) with login for the deal team

---
Built by **Abdelhamid Moltazim** · [moltazimdata.com](https://moltazimdata.com) · [GitHub](https://github.com/Moltazim-Data)
