import json
from pathlib import Path

import pytest

from screener.models import Company
from screener.rules import screen_company

ROOT = Path(__file__).resolve().parents[1]
MANDATE = json.loads((ROOT / "data/mandate.json").read_text())


def make(**kw):
    base = dict(company_id="T1", name="Test GmbH", country="AT", sector="Automation", revenue_eur_m=20.0,
                ebitda_margin=0.15, revenue_growth=0.10, employees=100, owner_type="Founder", description="")
    base.update(kw)
    return Company(**base)


def test_clear_fit():
    r = screen_company(make(), MANDATE)
    assert r.label == "fit" and r.score == 100
    assert "Meets all criteria" in r.rationale


@pytest.mark.parametrize("kw,reason", [
    ({"country": "IT"}, "country"),
    ({"sector": "Machinery"}, "sector"),
    ({"revenue_eur_m": 60}, "revenue"),
    ({"owner_type": "State"}, "owner"),
])
def test_hard_criteria_give_no_fit(kw, reason):
    r = screen_company(make(**kw), MANDATE)
    assert r.label == "no_fit" and r.score == 0
    assert reason in r.rationale


def test_one_soft_miss_is_maybe():
    r = screen_company(make(ebitda_margin=0.05), MANDATE)
    assert r.label == "maybe"


def test_two_soft_misses_is_no_fit():
    r = screen_company(make(ebitda_margin=0.04, revenue_growth=0.01), MANDATE)
    assert r.label == "no_fit"


def test_borderline_is_maybe_not_no_fit():
    r = screen_company(make(ebitda_margin=0.095), MANDATE)  # within 10% tolerance of 10%
    assert r.label == "maybe" and "Borderline" in r.rationale


def test_red_flag_downgrades_fit_to_maybe():
    r = screen_company(make(description="Pending litigation with a supplier."), MANDATE)
    assert r.label == "maybe" and "litigation" in r.checks["red_flags"]


def test_revenue_bounds_are_inclusive():
    assert screen_company(make(revenue_eur_m=5), MANDATE).label == "fit"
    assert screen_company(make(revenue_eur_m=50), MANDATE).label == "fit"
