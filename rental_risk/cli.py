"""Command line: python -m rental_risk {analyze,train,evaluate}"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def cmd_analyze(a):
    from .pipeline import Analyzer
    from .report import to_html, to_json, to_markdown
    analyzer = Analyzer(engine=a.engine)
    out_dir = Path(a.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    for f in a.files:
        rep = analyzer.analyze_file(f)
        stem = Path(f).stem
        written = []
        for fmt in a.format.split(","):
            fmt = fmt.strip()
            content = {"html": to_html, "md": to_markdown, "json": to_json}[fmt](rep)
            p = out_dir / f"{stem}.risk.{fmt}"
            p.write_text(content, encoding="utf-8")
            written.append(str(p))
        s = rep["summary"]
        print(f"{Path(f).name}: {s['rating']} risk | {s['risk_counts']['RISKY']} risky / {s['clauses']} clauses "
              f"| {len(rep['document_findings'])} whole-agreement findings | engine={rep['engine']}")
        if a.verbose:
            for c in rep["clauses"]:
                if c["risk"] == "RISKY":
                    print(f"  [{c['severity']:>6}] #{c['number'] or c['index']} {c['type_label']}: {c['explanation'][:140]}")
            for d in rep["document_findings"]:
                print(f"  [{d['severity']:>6}] DOC {d['title']}")
        print("  ->", ", ".join(written))


def cmd_prepare(a):
    from .prepare import prepare
    n = prepare(a.files, a.out, prefill=not a.blank)
    print(f"{n} clauses -> {a.out}")
    print("Next: open it in Excel/Sheets, correct the clause_type and risk columns, save, then run:")
    print(f"  python -m rental_risk train --data data/clauses.csv {a.out}")


def cmd_train(a):
    from collections import Counter
    from .ml import ClauseModel, load_dataset
    rows = load_dataset(a.data, report=True)
    if len(rows) < 20:
        raise SystemExit(f"Only {len(rows)} labelled clauses found; label more before training.")
    print("risk labels:", dict(Counter(r["risk"] for r in rows)))
    print("by source  :", dict(Counter(r["source"] for r in rows)))
    p = ClauseModel.train(rows).save(a.model)
    print(f"Trained on {len(rows)} labelled clauses -> {p}")


def cmd_evaluate(a):
    from .evaluate import main as eval_main
    eval_main(a.data, a.folds, a.out, test_path=a.test)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="rental_risk", description="Automated risk-clause detection for rental agreements")
    sub = ap.add_subparsers(dest="cmd", required=True)
    an = sub.add_parser("analyze", help="analyse agreements (.pdf, .docx, .txt)")
    an.add_argument("files", nargs="+")
    an.add_argument("--engine", default="auto", choices=["auto", "rules", "ml", "hybrid", "llm"])
    an.add_argument("--out", default="reports")
    an.add_argument("--format", default="html,md,json")
    an.add_argument("-v", "--verbose", action="store_true")
    an.set_defaults(fn=cmd_analyze)
    pr = sub.add_parser("prepare", help="turn agreements into a labelling sheet (CSV) pre-filled with suggestions")
    pr.add_argument("files", nargs="+", help="agreement files or folders (.pdf, .docx, .txt)")
    pr.add_argument("--out", default="data/to_label.xlsx", help=".xlsx (with dropdowns) or .csv")
    pr.add_argument("--blank", action="store_true", help="leave labels empty instead of pre-filling the system's guess")
    pr.set_defaults(fn=cmd_prepare)
    tr = sub.add_parser("train", help="train the ML clause model on one or more labelled CSVs")
    tr.add_argument("--data", nargs="+", default=[str(Path(__file__).resolve().parent.parent / "data" / "clauses.csv")],
                    help="labelled .csv/.xlsx files or folders of them")
    tr.add_argument("--model", default=str(Path(__file__).resolve().parent.parent / "models" / "clause_model.joblib"))
    tr.set_defaults(fn=cmd_train)
    ev = sub.add_parser("evaluate", help="cross-validated comparison of rules vs ML vs hybrid")
    ev.add_argument("--data", nargs="+", default=[str(Path(__file__).resolve().parent.parent / "data" / "clauses.csv")],
                    help="labelled CSV files or folders used for cross-validation / training")
    ev.add_argument("--test", nargs="+", default=None,
                    help="held-out labelled CSV(s); default data/clauses_test.csv")
    ev.add_argument("--folds", type=int, default=5)
    ev.add_argument("--out", default="reports/evaluation.md")
    ev.set_defaults(fn=cmd_evaluate)
    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
