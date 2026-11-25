"""Excel deliverable in a fixed house style: Summary, Screening, Mandate sheets."""
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

NAVY, ACCENT = "14284B", "E8A33D"
FILL = {"fit": "D9F2E3", "maybe": "FFF2CC", "no_fit": "F8D7DA"}
THIN = Side(style="thin", color="D5DCE8")


def _header(ws, row, values):
    for col, v in enumerate(values, start=1):
        cell = ws.cell(row=row, column=col, value=v)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor=NAVY)
        cell.alignment = Alignment(vertical="center", wrap_text=True)


def export_excel(path, companies, results, mandate, ev=None):
    by_id = {c.company_id: c for c in companies}
    wb = Workbook()

    # Summary
    ws = wb.active
    ws.title = "Summary"
    ws["A1"] = f"Target screening – mandate {mandate['mandate_id']}"
    ws["A1"].font = Font(bold=True, size=14, color=NAVY)
    ws["A2"] = mandate["target_profile"]
    ws["A2"].font = Font(italic=True, color="7A8499")
    _header(ws, 4, ["Label", "Companies", "Share"])
    total = len(results)
    for i, lab in enumerate(["fit", "maybe", "no_fit"], start=5):
        n = sum(r.label == lab for r in results)
        ws.cell(i, 1, lab).fill = PatternFill("solid", fgColor=FILL[lab])
        ws.cell(i, 2, n)
        ws.cell(i, 3, f"=B{i}/B8").number_format = "0%"
    ws.cell(8, 1, "Total").font = Font(bold=True)
    ws.cell(8, 2, "=SUM(B5:B7)").font = Font(bold=True)
    if ev and ev.get("n"):
        ws["A10"] = "Quality check vs analyst labels"
        ws["A10"].font = Font(bold=True, color=NAVY)
        ws["A11"], ws["B11"] = "Labelled companies", ev["n"]
        ws["A12"], ws["B12"] = "Accuracy", ev["accuracy"]
        ws["B12"].number_format = "0.0%"
        ws["A13"], ws["B13"] = "Dangerous errors (no_fit -> fit)", ev["dangerous_errors"]
    ws.column_dimensions["A"].width = 34
    ws.column_dimensions["B"].width = 14
    ws.column_dimensions["C"].width = 10

    # Screening
    ws = wb.create_sheet("Screening")
    cols = ["ID", "Company", "Country", "Sector", "Revenue (EUR m)", "EBITDA margin", "Growth",
            "Employees", "Owner", "Label", "Score", "Source", "Rationale", "Website evidence"]
    _header(ws, 1, cols)
    order = {"fit": 0, "maybe": 1, "no_fit": 2}
    for row, r in enumerate(sorted(results, key=lambda r: (order[r.label], -r.score)), start=2):
        c = by_id[r.company_id]
        vals = [c.company_id, c.name, c.country, c.sector, c.revenue_eur_m, c.ebitda_margin, c.revenue_growth,
                c.employees, c.owner_type, r.label, r.score, r.source, r.rationale, r.evidence]
        for col, v in enumerate(vals, start=1):
            cell = ws.cell(row, col, v)
            cell.border = Border(top=THIN, bottom=THIN, left=THIN, right=THIN)
            cell.alignment = Alignment(vertical="top", wrap_text=(col >= 13))
        ws.cell(row, 6).number_format = "0%"
        ws.cell(row, 7).number_format = "0%"
        ws.cell(row, 5).number_format = "0.0"
        ws.cell(row, 10).fill = PatternFill("solid", fgColor=FILL[r.label])
    widths = [7, 32, 8, 18, 10, 9, 8, 10, 14, 9, 7, 10, 60, 60]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "C2"
    ws.auto_filter.ref = f"A1:N{len(results) + 1}"

    # Mandate
    ws = wb.create_sheet("Mandate")
    _header(ws, 1, ["Criterion", "Value"])
    rows = [
        ("Buyer", mandate["buyer"]),
        ("Countries (hard)", ", ".join(mandate["hard_criteria"]["countries"])),
        ("Sectors (hard)", ", ".join(mandate["hard_criteria"]["sectors"])),
        ("Revenue EUR m (hard)", f"{mandate['hard_criteria']['revenue_eur_m']['min']}–{mandate['hard_criteria']['revenue_eur_m']['max']}"),
        ("Excluded owners (hard)", ", ".join(mandate["hard_criteria"]["excluded_owners"])),
        ("Min EBITDA margin (soft)", f"{mandate['soft_criteria']['min_ebitda_margin']:.0%}"),
        ("Min revenue growth (soft)", f"{mandate['soft_criteria']['min_revenue_growth']:.0%}"),
        ("Max employees (soft)", mandate["soft_criteria"]["max_employees"]),
        ("Red flags", ", ".join(mandate["red_flags"])),
    ]
    for i, (k, v) in enumerate(rows, start=2):
        ws.cell(i, 1, k).font = Font(bold=True)
        ws.cell(i, 2, v)
    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 70

    wb.save(path)
    return path
