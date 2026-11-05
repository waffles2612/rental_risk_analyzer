"""Turn agreements (.pdf/.docx/.txt) into a labelling sheet.

Each clause becomes one row, pre-filled with the system's current guess, so annotators only correct
what is wrong. Columns: id, text, clause_type, risk, source, suggested_type, suggested_risk, reasons.
Annotators edit `clause_type` and `risk`; leave a row's labels blank to exclude it from training.
"""
from __future__ import annotations

import csv
from pathlib import Path

from .ingest import read_document, segment
from .pipeline import Analyzer

FIELDS = ["id", "text", "clause_type", "risk", "source", "suggested_type", "suggested_risk", "reasons"]
SUFFIXES = {".pdf", ".docx", ".txt"}


def _files(paths) -> list[Path]:
    out = []
    for p in map(Path, paths):
        out += sorted(x for x in p.rglob("*") if x.suffix.lower() in SUFFIXES) if p.is_dir() else [p]
    return out


def prepare(paths, out_csv: str | Path, prefill: bool = True) -> int:
    analyzer = Analyzer(engine="rules")
    rows = []
    for f in _files(paths):
        try:
            text = read_document(f)
        except Exception as e:  # unreadable or scanned file: report and carry on
            print(f"  skipped {f.name}: {e}")
            continue
        rep = analyzer.analyze_text(text, title=f.stem)
        for c in rep["clauses"]:
            body = f"{c['heading']}: {c['text']}" if c["heading"] else c["text"]
            rows.append({
                "id": f"{f.stem}-{c['index']:03d}", "text": body,
                "clause_type": c["clause_type"] if prefill else "", "risk": c["risk"] if prefill else "",
                "source": f.name, "suggested_type": c["clause_type"], "suggested_risk": c["risk"],
                "reasons": "; ".join(h["title"] for h in c["findings"]),
            })
        print(f"  {f.name}: {len(rep['clauses'])} clauses")
    out_csv = Path(out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    if out_csv.suffix.lower() == ".xlsx":
        write_xlsx(rows, out_csv)
    else:
        with open(out_csv, "w", newline="", encoding="utf-8-sig") as fh:  # utf-8-sig so Excel shows the rupee sign
            w = csv.DictWriter(fh, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(rows)
    return len(rows)


TYPES = ["RENT", "DEPOSIT", "TERMINATION", "RENEWAL", "MAINTENANCE", "PENALTY", "ENTRY", "LIABILITY", "USE", "OTHER"]
RISKS = ["RISKY", "NEUTRAL", "TENANT_FAVORABLE"]


def write_xlsx(rows: list[dict], path: Path) -> None:
    """Labelling workbook: dropdowns on clause_type/risk, wrapped clause text, frozen header, a 'Guide' sheet."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.worksheet.datavalidation import DataValidation

    wb = Workbook()
    ws = wb.active
    ws.title = "Label"
    ws.append(FIELDS)
    for r in rows:
        ws.append([r.get(f, "") for f in FIELDS])
    head_fill, edit_fill = PatternFill("solid", fgColor="14213A"), PatternFill("solid", fgColor="FFF2B3")
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = head_fill
    widths = {"A": 22, "B": 90, "C": 16, "D": 20, "E": 28, "F": 16, "G": 20, "H": 40}
    for col, w in widths.items():
        ws.column_dimensions[col].width = w
    n = len(rows) + 1
    for row in ws.iter_rows(min_row=2, max_row=n):
        row[1].alignment = Alignment(wrap_text=True, vertical="top")
        for c in (row[0], row[2], row[3], row[4], row[5], row[6], row[7]):
            c.alignment = Alignment(vertical="top", wrap_text=c.column_letter == "H")
        row[2].fill = edit_fill
        row[3].fill = edit_fill
    ws.freeze_panes = "C2"
    ws.auto_filter.ref = f"A1:H{n}"
    dv_t = DataValidation(type="list", formula1='"' + ",".join(TYPES) + '"', allow_blank=True,
                          showErrorMessage=True, errorTitle="Clause type", error="Pick a type from the list.")
    dv_r = DataValidation(type="list", formula1='"' + ",".join(RISKS) + '"', allow_blank=True,
                          showErrorMessage=True, errorTitle="Risk", error="Pick RISKY, NEUTRAL or TENANT_FAVORABLE.")
    ws.add_data_validation(dv_t)
    ws.add_data_validation(dv_r)
    dv_t.add(f"C2:C{n}")
    dv_r.add(f"D2:D{n}")
    g = wb.create_sheet("Guide")
    guide = [
        ("How to label", ""),
        ("1", "Edit only the yellow columns: clause_type and risk. They are pre-filled with the system's guess (see suggested_*)."),
        ("2", "Judge each clause from the TENANT's point of view. Clear a row's labels to leave it out of training."),
        ("3", "Do not just accept the guesses: if you never change them, the model only learns to copy the rules."),
        ("", ""),
        ("risk", "meaning"),
        ("RISKY", "Shifts cost, liability or control onto the tenant beyond what is usual, is one-sided, or is vague in a way that can hurt the tenant."),
        ("NEUTRAL", "Standard, balanced or purely factual (parties, address, rent amount, dates)."),
        ("TENANT_FAVORABLE", "Adds protection for the tenant beyond the usual."),
        ("", ""),
        ("clause_type", "use for"),
        ("RENT", "rent amount, due date, payment, utilities, taxes, advance"),
        ("DEPOSIT", "security deposit, refund, deductions"),
        ("TERMINATION", "ending the agreement, notice to vacate, lock-in, eviction"),
        ("RENEWAL", "term length, renewal, extension, increase on renewal"),
        ("MAINTENANCE", "repairs, upkeep, painting, wear and tear, fixtures"),
        ("PENALTY", "late fees, interest on delay, fines, overstay charges"),
        ("ENTRY", "landlord visits, inspections, keys"),
        ("LIABILITY", "indemnity, responsibility for loss/damage/injury, legal costs"),
        ("USE", "residential use, subletting, guests, pets, house rules"),
        ("OTHER", "parties, addresses, date, stamp duty, disputes, schedule of property, anything else"),
    ]
    for row in guide:
        g.append(row)
    for r in (1, 6, 11):
        g.cell(row=r, column=1).font = Font(bold=True)
        g.cell(row=r, column=2).font = Font(bold=True)
    g.column_dimensions["A"].width = 20
    g.column_dimensions["B"].width = 110
    wb.save(path)
