from dataclasses import dataclass, field, asdict

LABELS = ("fit", "maybe", "no_fit")


@dataclass
class Company:
    company_id: str
    name: str
    country: str
    sector: str
    revenue_eur_m: float
    ebitda_margin: float
    revenue_growth: float
    employees: int
    owner_type: str
    description: str

    @classmethod
    def from_row(cls, row: dict) -> "Company":
        return cls(
            company_id=row["company_id"].strip(),
            name=row["name"].strip(),
            country=row["country"].strip().upper(),
            sector=row["sector"].strip(),
            revenue_eur_m=float(row["revenue_eur_m"]),
            ebitda_margin=float(row["ebitda_margin"]),
            revenue_growth=float(row["revenue_growth"]),
            employees=int(row["employees"]),
            owner_type=row["owner_type"].strip(),
            description=row.get("description", "").strip(),
        )


@dataclass
class Result:
    company_id: str
    name: str
    label: str
    rationale: str
    source: str = "rules"            # "rules" or "rules+llm"
    rule_label: str = ""
    score: int = 0                    # 0-100, higher = better fit
    evidence: str = ""                # website passages found by retrieval (RAG)
    checks: dict = field(default_factory=dict)
    evidence_items: list = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("checks")
        d.pop("evidence_items")
        return d
