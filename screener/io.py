import csv
import json
from pathlib import Path

from .models import Company, LABELS

REQUIRED = ["company_id", "name", "country", "sector", "revenue_eur_m",
            "ebitda_margin", "revenue_growth", "employees", "owner_type"]


def load_companies(path: str | Path) -> list[Company]:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"Missing columns in {path}: {missing}")
        companies, errors = [], []
        for i, row in enumerate(reader, start=2):
            try:
                companies.append(Company.from_row(row))
            except (ValueError, KeyError) as e:
                errors.append(f"line {i}: {e}")
    if errors:
        raise ValueError("Invalid rows:\n" + "\n".join(errors))
    ids = [c.company_id for c in companies]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate company_id values found")
    return companies


def load_mandate(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_labels(path: str | Path) -> dict[str, str]:
    with open(path, newline="", encoding="utf-8") as f:
        labels = {r["company_id"].strip(): r["analyst_label"].strip() for r in csv.DictReader(f)}
    bad = {k: v for k, v in labels.items() if v not in LABELS}
    if bad:
        raise ValueError(f"Unknown labels: {bad}")
    return labels
