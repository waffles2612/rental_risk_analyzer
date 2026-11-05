"""Evaluation: rule baseline vs trained model vs hybrid, with stratified k-fold cross-validation.

The rules are fixed (not trained), so they are scored on every clause. The model is scored on held-out
folds only, so its numbers are not inflated by seeing the test clause during training.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_recall_fscore_support
from sklearn.model_selection import StratifiedKFold

from .doccheck import run_document_checks
from .ml import ClauseModel, load_dataset
from .pipeline import FOLD_INTO_CLAUSES
from .rules import FAVORABLE, NEUTRAL, RISKY, classify_type, match_rules, risk_from_hits, second_best_type

RISK_LABELS = [RISKY, NEUTRAL, FAVORABLE]


def rule_predict(text: str, ctype: str | None = None) -> tuple[str, str]:
    """Rule baseline on a single clause, including the cross-clause checks that can fire within one clause."""
    rtype, scores = classify_type(text)
    use_type = ctype or rtype
    hits = [h.to_dict() for h in match_rules(text, use_type, secondary=second_best_type(scores) if use_type == rtype else rtype)]
    for f in run_document_checks([{"index": 1, "text": text, "clause_type": use_type}], check_missing=False):
        if f.risk == RISKY and f.check_id in FOLD_INTO_CLAUSES and not (f.check_id == "DOC_DEPOSIT_RATIO" and use_type != "DEPOSIT"):
            hits.append({"risk": RISKY})
    return rtype, risk_from_hits(hits)


from .pipeline import hybrid_risk as combine  # noqa: E402  (same policy as the live pipeline)


def _metrics(y_true, y_pred, labels):
    p, r, f, s = precision_recall_fscore_support(y_true, y_pred, labels=labels, zero_division=0)
    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "macro_f1": f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0),
        "per_class": {l: (p[i], r[i], f[i], int(s[i])) for i, l in enumerate(labels)},
        "cm": confusion_matrix(y_true, y_pred, labels=labels),
    }


def run(data_path, folds: int = 5, seed: int = 13, test_path=None) -> dict:
    rows = load_dataset(data_path)
    texts = [r["text"] for r in rows]
    y_type = np.array([r["clause_type"] for r in rows])
    y_risk = np.array([r["risk"] for r in rows])
    type_labels = sorted(set(y_type))

    # Rule baseline (no training)
    rule_types, rule_risks = zip(*(rule_predict(t) for t in texts))

    # Model, out-of-fold
    ml_type = np.empty(len(rows), dtype=object)
    ml_risk = np.empty(len(rows), dtype=object)
    ml_conf = np.zeros(len(rows))
    ml_prisky = np.zeros(len(rows))
    skf = StratifiedKFold(n_splits=folds, shuffle=True, random_state=seed)
    for tr, te in skf.split(texts, y_risk):
        model = ClauseModel.train([rows[i] for i in tr])
        for i in te:
            p = model.predict(texts[i])
            ml_type[i], ml_risk[i], ml_conf[i] = p["clause_type"], p["risk"], p["type_confidence"]
            ml_prisky[i] = p["risk_probs"].get(RISKY, 0.0)

    # Hybrid: model's type when confident, rules re-run with that type, OR-combined risk
    hy_type, hy_risk = [], []
    for i, t in enumerate(texts):
        ct = ml_type[i] if (rule_types[i] == "OTHER" or ml_conf[i] >= 0.5) else rule_types[i]
        _, rr = rule_predict(t, ct)
        hy_type.append(ct)
        hy_risk.append(combine(rr, ml_risk[i], ml_prisky[i]))

    systems = {
        "Rule baseline": (list(rule_types), list(rule_risks)),
        "Trained model (TF-IDF + LR)": (list(ml_type), list(ml_risk)),
        "Hybrid (rules + model)": (hy_type, hy_risk),
    }
    results = {name: {"type": _metrics(y_type, tp, type_labels), "risk": _metrics(y_risk, rp, RISK_LABELS)}
               for name, (tp, rp) in systems.items()}
    test = None
    tp = [test_path] if isinstance(test_path, (str, Path)) else (test_path or [])
    if tp and all(Path(p).exists() for p in tp):
        test = held_out(rows, load_dataset(tp))
    misses = [(rows[i]["id"], rows[i]["text"], y_risk[i], rule_risks[i]) for i in range(len(rows)) if rule_risks[i] != y_risk[i]]
    return {"n": len(rows), "folds": folds, "type_labels": type_labels, "results": results,
            "label_counts": {str(k): v for k, v in Counter(y_risk).items()}, "rule_misses": misses, "test": test}


def held_out(dev_rows: list[dict], test_rows: list[dict]) -> dict:
    """Train on all dev clauses, score every system once on the untouched test set."""
    model = ClauseModel.train(dev_rows)
    texts = [r["text"] for r in test_rows]
    yt = [r["clause_type"] for r in test_rows]
    yr = [r["risk"] for r in test_rows]
    systems = {"Rule baseline": ([], []), "Trained model (TF-IDF + LR)": ([], []), "Hybrid (rules + model)": ([], [])}
    misses = []
    for r, t in zip(test_rows, texts):
        rt, rr = rule_predict(t)
        p = model.predict(t)
        ct = p["clause_type"] if (rt == "OTHER" or p["type_confidence"] >= 0.5) else rt
        _, hr = rule_predict(t, ct)
        hy = combine(hr, p["risk"], p["risk_probs"].get(RISKY, 0.0))
        for name, (a, b) in zip(systems, [(rt, rr), (p["clause_type"], p["risk"]), (ct, hy)]):
            systems[name][0].append(a)
            systems[name][1].append(b)
        if hy != r["risk"]:
            misses.append((r["id"], t, r["risk"], hy))
    type_labels = sorted(set(yt))
    return {"n": len(test_rows),
            "results": {n: {"type": _metrics(yt, tp, type_labels), "risk": _metrics(yr, rp, RISK_LABELS)} for n, (tp, rp) in systems.items()},
            "hybrid_misses": misses}


def _summary_table(results: dict) -> list[str]:
    L = ["| System | Type accuracy | Type macro-F1 | Risk accuracy | Risk macro-F1 | RISKY precision | RISKY recall |",
         "|---|---|---|---|---|---|---|"]
    for name, r in results.items():
        rp, rr, _, _ = r["risk"]["per_class"][RISKY]
        L.append(f"| {name} | {r['type']['accuracy']:.2f} | {r['type']['macro_f1']:.2f} | {r['risk']['accuracy']:.2f} | "
                 f"{r['risk']['macro_f1']:.2f} | {rp:.2f} | {rr:.2f} |")
    return L


def to_markdown(ev: dict) -> str:
    L = ["# Evaluation\n"]
    if ev.get("test"):
        L += [f"## Held-out test set ({ev['test']['n']} clauses, never used for rule tuning or training)\n"]
        L += _summary_table(ev["test"]["results"])
        L += ["", "RISKY recall matters most: a missed risky clause costs the tenant more than a false alarm.\n"]
    L += [f"## Development set ({ev['n']} clauses)\n",
          f"Model scored with {ev['folds']}-fold stratified cross-validation. Rules were tuned on this set, so their dev numbers are optimistic. "
          f"Risk labels: {ev['label_counts']}\n"]
    L += _summary_table(ev["results"]) + [""]
    for name, r in ev["results"].items():
        L += [f"## {name}: risk per class\n", "| Label | Precision | Recall | F1 | Support |", "|---|---|---|---|---|"]
        for lab, (p, rc, f, s) in r["risk"]["per_class"].items():
            L.append(f"| {lab} | {p:.2f} | {rc:.2f} | {f:.2f} | {s} |")
        cm = r["risk"]["cm"]
        L += ["", "Confusion matrix (rows = true, cols = predicted: " + ", ".join(RISK_LABELS) + ")", "", "```"]
        L += ["  ".join(f"{v:>4}" for v in row) for row in cm]
        L += ["```", ""]
    L += ["## Where the rule baseline disagrees with the labels\n",
          "Use these to write new rules or fix labels (dev set only).\n", "| id | true | rules | clause |", "|---|---|---|---|"]
    for cid, text, t, p in ev["rule_misses"]:
        L.append(f"| {cid} | {t} | {p} | {text.replace('|', '/')} |")
    if ev.get("test") and ev["test"]["hybrid_misses"]:
        L += ["", "## Held-out errors (hybrid)\n", "| id | true | predicted | clause |", "|---|---|---|---|"]
        for cid, text, t, p in ev["test"]["hybrid_misses"]:
            L.append(f"| {cid} | {t} | {p} | {text.replace('|', '/')} |")
    L += ["", "> Caveat: the seed dataset and the rules were written by the same author, so rule-baseline scores are likely optimistic. "
          "Re-run on clauses from real agreements labelled by your team before quoting these numbers."]
    return "\n".join(L)


def main(data_path, folds=5, out="reports/evaluation.md", test_path=None):
    if test_path is None:
        first = data_path[0] if isinstance(data_path, (list, tuple)) else data_path
        test_path = Path(first).with_name("clauses_test.csv") if Path(first).is_file() else Path(first) / "clauses_test.csv"
    ev = run(data_path, folds, test_path=test_path)
    md = to_markdown(ev)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(md, encoding="utf-8")
    print(md.split("## Rule baseline: risk")[0])
    print(f"Full report -> {out}")
    return ev
