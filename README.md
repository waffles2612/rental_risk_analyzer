# Automated Risk Clause Detection and Explanation for Rental Agreements

A proactive, document-level system that reads a whole rental agreement, classifies every clause, flags the risky ones, and explains each risk in plain English, with a concrete change the tenant can ask for.

It follows the four-stage pipeline from the project deck:

| Deck stage | Where it lives | What it does |
|---|---|---|
| 01 Ingestion & segmentation | `rental_risk/ingest.py` | Reads `.pdf`, `.docx`, `.txt`; splits into clauses using numbering (`1.`, `2.3`, `(a)`, `Clause 4`), headings (`SECURITY DEPOSIT`), then paragraphs or sentences as fallbacks. Drops signature blocks. |
| 02 Clause classification | `rules.py` (baseline), `ml.py` (upgrade) | 10 types: RENT, DEPOSIT, TERMINATION, RENEWAL, MAINTENANCE, PENALTY, ENTRY, LIABILITY, USE, OTHER (the deck's five plus the ones real agreements need). |
| 03 Risk assessment | `rules.json` + `doccheck.py` | RISKY / NEUTRAL / TENANT_FAVORABLE per clause, with severity. Cross-clause checks: deposit vs rent, unequal notice periods, very short notice, missing clauses. |
| 04 Flagging & explanation | `pipeline.py`, `report.py` | Plain-English explanation built from the matched findings and the clause's own numbers ("Key numbers: 15 days, ₹25,000"), plus an "Ask for" line. HTML report highlights the exact wording that triggered each flag. |

Engines (deck: baseline → upgrade path):

- `rules`: keyword + pattern baseline, 65 rules in `rental_risk/rules.json`. Every flag comes with a reason.
- `ml`: TF-IDF + logistic regression for type and risk. Explains itself by naming the words that pushed a clause towards "risky".
- `hybrid` (default once a model is trained): rules first, model fills the gaps. A rule-detected risk is never dropped.
- `llm`: few-shot classification + explanation with Claude (`pip install anthropic`, set `ANTHROPIC_API_KEY`; model set by `RENTAL_RISK_LLM_MODEL`, default `claude-sonnet-5-5`). Not exercised in the results below.

## Quick start

```bash
pip install -r requirements.txt
python -m rental_risk train                      # trains models/clause_model.joblib from data/clauses.csv
python -m rental_risk analyze data/sample_agreements/leave_and_license_risky.pdf -v
python -m rental_risk evaluate                   # writes reports/evaluation.md
python -m unittest discover -s tests -v
```

`analyze` writes `<name>.risk.html`, `.md` and `.json` into `reports/`. Options: `--engine rules|ml|hybrid|llm`, `--format html,md,json`, `--out DIR`.

From Python:

```python
from rental_risk import Analyzer
report = Analyzer(engine="hybrid").analyze_file("agreement.pdf")
for c in report["clauses"]:
    if c["risk"] == "RISKY":
        print(c["number"], c["type_label"], c["severity"], c["explanation"], c["ask"])
```

Dashboard: `demo/dashboard.html` opens directly in any browser (double-click, works offline): upload or paste agreements and clause lists, filter, and click a clause to see why it was flagged. `demo/artifact/` holds the same pages as fragments for hosting.

Browser demo: `demo/index.html` runs the rule engine fully client-side (paste text, no upload). It embeds the same `rules.json`; rebuild with `python demo/build_demo.py` after editing rules. `tests/test_demo_parity.py` checks the JavaScript and Python engines give identical results on all 199 labelled clauses and the sample agreements.

## Results

Held-out test set: 60 clauses written before the rules were tuned and never used for tuning or training. Model trained on the 139-clause development set.

| System | Type accuracy | Risk accuracy | Risk macro-F1 | RISKY precision | RISKY recall |
|---|---|---|---|---|---|
| Rule baseline | 0.78 | 0.80 | 0.82 | 1.00 | 0.68 |
| Trained model (TF-IDF + LR) | 0.85 | 0.70 | 0.65 | 0.76 | 0.81 |
| **Hybrid (rules + model)** | **0.88** | **0.87** | **0.85** | 0.86 | **0.97** |

RISKY recall is the number that matters most: a missed risky clause costs the tenant more than a false alarm. Before rule tuning on the dev set, the rule baseline scored 0.52 risk accuracy and 0.32 RISKY recall on the same held-out set. Full per-class tables, confusion matrices and every disagreement are in `reports/evaluation.md`.

**Read these numbers with care.** Both datasets and the rules were written by one author, so they share phrasing habits, and 60 test clauses is small. Treat this as a working baseline; the numbers to quote in a write-up should come from real agreements annotated by your team (deck step 02 "Label").

On the sample agreements: the one-sided leave-and-licence agreement is rated **High** (16 of 19 clauses risky, plus a 10× deposit and 90-vs-15-day notice imbalance), the balanced lease **Low** (0 risky, 15 tenant-favourable), and the informal room rental **Moderate**.

## Data

- `data/clauses.csv`: development set, 139 clauses (`id,text,clause_type,risk,source`). Rebuild with `python data/build_dataset.py`.
- `data/clauses_test.csv`: held-out set, 60 clauses. Keep it untouched by tuning.
- `data/sample_agreements/`: three agreements (`.txt`, plus `.pdf` and `.docx` copies to exercise ingestion).

Labels are from the tenant's point of view. RISKY: shifts cost, liability or control onto the tenant beyond what is usual, or is vague in a way that can hurt them. TENANT_FAVORABLE: adds protection beyond the usual. Otherwise NEUTRAL.

To grow the dataset (deck step 04 "Expand"): add rows to a CSV with the same columns, run `python -m rental_risk train --data your.csv`, and re-run `evaluate`. The "Where the rule baseline disagrees" table in the evaluation report is the to-do list for new rules.

## Training on more data

1. **Collect** agreements (`.pdf`, `.docx`, `.txt`) into a folder, e.g. `my_agreements/`. Remove names, addresses and ID numbers.
2. **Make a labelling sheet**: `python -m rental_risk prepare my_agreements --out data/my_labels.xlsx`
   One row per clause, pre-filled with the system's guess (`--blank` to leave labels empty). An `.xlsx` gets dropdowns for the labels and a Guide sheet; use `.csv` if you prefer.
3. **Label**: open it in Excel or Google Sheets, correct the yellow `clause_type` and `risk` columns using `data/LABELLING_GUIDE.md`, and save (keep `.xlsx`, or save as CSV). Blank rows are skipped.
4. **Train** on the old and new data together:
   `python -m rental_risk train --data data/clauses.csv data/my_labels.xlsx` (several files, or a folder of `.csv`/`.xlsx`, also work).
   Invalid labels are listed and skipped; duplicate clauses are counted once.
5. **Evaluate** on agreements kept out of training:
   `python -m rental_risk evaluate --data data/clauses.csv data/my_labels.csv --test data/my_test_labels.csv`
6. `analyze` now uses the new model automatically.

## Adding or changing a rule

Edit `rental_risk/rules.json`. Each rule has `id`, `types` (clause types it applies to, or `"*"`), `pattern`, optional `unless` (suppresses the rule), optional `value_min` / `value_max` (compares the first captured number, digits or words like "fifteen"), `risk`, `severity`, `title`, `explanation`, `ask`. Placeholders `{T}` (tenant/lessee/licensee), `{L}` (landlord/lessor/licensor/owner), `{R}` (rent/licence fee) and `{S}` (span within a sentence) are expanded at load. Patterns must work in both Python and JavaScript: no lookbehind, no named groups (a test enforces this). Then run the tests and `python demo/build_demo.py`.

## Layout

```
rental_risk/   ingest.py  rules.py  rules.json  doccheck.py  pipeline.py  ml.py  llm.py  report.py  evaluate.py  cli.py
data/          clauses.csv  clauses_test.csv  build_dataset.py  build_testset.py  sample_agreements/
models/        clause_model.joblib (created by `train`)
demo/          template.html  build_demo.py  index.html
reports/       generated reports and evaluation.md
tests/         test_pipeline.py  test_demo_parity.py
```

## Limitations

- Scanned PDFs need OCR first (e.g. `ocrmypdf`); the tool says so instead of returning nothing.
- Rules are tuned to Indian leave-and-licence and lease wording (Licensor/Licensee, lock-in, Rs/₹ amounts). Other jurisdictions will need new rules and data.
- The Model Tenancy Act, 2021 reference (two months' deposit) applies only in states that have adopted it.
- This is a screening aid, not legal advice.
