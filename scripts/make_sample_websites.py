"""Create fictional company websites (HTML) for the RAG demo.

Every company gets an About / Products / Customers / News page section.
A few companies get news items that matter for M&A screening
(litigation, sanctions review, finished restructuring, customer concentration).
All content is invented sample data.
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "websites"

SPECIAL_NEWS = {
    "C008": ["A former distributor filed a patent infringement lawsuit against Tirol IoT Solutions in 2026. "
             "The claim covers the core sensor technology, and the first court hearing is scheduled for spring 2027.",
             "Management expects the legal dispute to take at least two years."],
    "C027": ["German authorities opened a sanctions review of Frankfurt Fabrikdaten because one minority shareholder "
             "is a holding company registered in Russia. Payments to this shareholder are currently frozen.",
             "Until the review is closed, the company cannot sign new public-sector contracts."],
    "C019": ["Hamburg Supply Chain IT completed its restructuring programme in 2024. Two loss-making units were sold, "
             "and the company has been profitable every quarter since Q3 2024.",
             "A new CFO joined in 2025 and the bank loans were refinanced on normal terms."],
    "C014": ["Bodensee Vision renewed its framework contract with its largest automotive customer until 2029. "
             "This single customer accounts for 62% of annual revenue.",
             "The company plans to win two new customers in electronics manufacturing to reduce this dependency."],
    "C029": ["Graz Industrial AI reached operational break-even in 2025 after three years of losses, "
             "driven by subscription growth of 40%."],
    "C006": ["Revenue growth was flat for the second year. The company is preparing a cloud version of its ERP add-ons "
             "to restart growth."],
    "C005": ["Margins came under pressure because hourly rates for PLC programming were not increased in 2025."],
    "C009": ["Stadtwerke Digital remains fully owned by the municipal utility; a sale is not planned."],
}


def page(c: dict) -> str:
    news = SPECIAL_NEWS.get(c["company_id"], [f"{c['name']} opened a new office and hired engineers in 2026."])
    news_html = "".join(f"<p>{n}</p>" for n in news)
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>{c['name']}</title>
<style>nav, footer {{color:#888}}</style><script>console.log('tracking');</script></head>
<body>
<nav>Home | About | Products | Customers | News | Contact</nav>
<section id="about"><h2>About us</h2>
<p>{c['name']} is based in {c['country']} and works in {c['sector'].lower()}. {c['description']}</p>
<p>The company employs about {c['employees']} people and is owned by its {c['owner_type'].lower()} shareholders.</p></section>
<section id="products"><h2>Products</h2>
<p>Our products help manufacturers collect machine data, plan production and reduce downtime.</p></section>
<section id="customers"><h2>Customers</h2>
<p>We serve industrial customers across Europe, mainly in automotive, food, pharma and machine building.</p></section>
<section id="news"><h2>News</h2>{news_html}</section>
<footer>Imprint · Privacy · Cookie settings</footer>
</body></html>"""


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with open(ROOT / "data" / "companies.csv", newline="", encoding="utf-8") as f:
        for c in csv.DictReader(f):
            (OUT / f"{c['company_id']}.html").write_text(page(c), encoding="utf-8")
    print(f"Wrote {len(list(OUT.glob('*.html')))} sample websites to {OUT}")


if __name__ == "__main__":
    main()
