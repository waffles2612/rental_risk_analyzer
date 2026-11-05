"""Evaluate on the labelled REAL agreements with agreement-grouped cross-validation.

python scripts/eval_real.py data/real_agreements_to_label.xlsx [--authored data/clauses.csv] [--synthetic data/synthetic.xlsx]

- Splits by agreement (GroupKFold), so no agreement contributes to both train and test.
- Reports all agreements and Indian-only (agreements are tagged by currency/place/vocabulary markers).
- Systems: rules; classifier trained on authored data only; classifier trained on real training folds
  (+ authored + synthetic); hybrid of rules and that classifier (same fixed policy as the pipeline, tau = 0.6).
- Also reports binary RISKY-vs-rest, because the tenant-favourable class is very small.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from sklearn.metrics import accuracy_score, f1_score, precision_recall_fscore_support
from sklearn.model_selection import GroupKFold

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rental_risk.ml import ClauseModel, load_dataset  # noqa: E402
from rental_risk.pipeline import hybrid_risk  # noqa: E402
from rental_risk.rules import RISKY, classify_type, match_rules, risk_from_hits, second_best_type  # noqa: E402

LABELS = ["RISKY", "NEUTRAL", "TENANT_FAVORABLE"]
_IN = re.compile(r"\bRs\.?|₹|rupees|Bangalore|Bengaluru|Chennai|Hyderabad|Mumbai|Pune|Delhi|Kolkata|lessee|licensee|lessor|licensor", re.I)
_FX = re.compile(r"\bRM\s?\d|Ringgit|Manila|Philippine|\$\s?\d|dollars|Management shall|Resident\(s\)", re.I)


def region_of(texts: list[str]) -> str:
    t = " ".join(texts)
    return "foreign" if len(_FX.findall(t)) > len(_IN.findall(t)) else "india"


def rules_predict(text):
    ct, sc = classify_type(text)
    return ct, risk_from_hits(match_rules(text, ct, secondary=second_best_type(sc)))


def metrics(y, p):
    pr, rc, f, s = precision_recall_fscore_support(y, p, labels=LABELS, zero_division=0)
    yb = [v == RISKY for v in y]; pb = [v == RISKY for v in p]
    bp, br, bf, _ = precision_recall_fscore_support(yb, pb, average="binary", zero_division=0)
    return {"acc": accuracy_score(y, p), "macro_f1": f1_score(y, p, labels=LABELS, average="macro", zero_division=0),
            "risky_p": pr[0], "risky_r": rc[0], "risky_f1": f[0], "fav_f1": f[2], "bin_f1": bf, "n": len(y),
            "n_risky": int(s[0])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("real")
    ap.add_argument("--authored", nargs="*", default=["data/clauses.csv", "data/clauses_test.csv"])
    ap.add_argument("--synthetic", nargs="*", default=[])
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--out", default="reports/real_evaluation.md")
    a = ap.parse_args()

    real = load_dataset(a.real, report=True)
    authored = load_dataset(a.authored) if a.authored else []
    synth = load_dataset(a.synthetic) if a.synthetic else []
    by_src = defaultdict(list)
    for r in real:
        by_src[r["source"]].append(r["text"])
    region = {s: region_of(t) for s, t in by_src.items()}
    groups = np.array([r["source"] for r in real])
    y = [r["risk"] for r in real]

    # fixed predictions
    rp = [rules_predict(r["text"])[1] for r in real]
    m_auth = ClauseModel.train(authored + synth)
    ap_auth = [m_auth.predict(r["text"])["risk"] for r in real]

    # grouped CV for real-trained model + hybrid
    mp = [None] * len(real); hp = [None] * len(real)
    for tr, te in GroupKFold(n_splits=a.folds).split(real, y, groups):
        model = ClauseModel.train([real[i] for i in tr] + authored + synth)
        for i in te:
            pred = model.predict(real[i]["text"])
            mp[i] = pred["risk"]
            hp[i] = hybrid_risk(rp[i], pred["risk"], pred["risk_probs"].get(RISKY, 0.0))

    systems = {"Rules": rp, "Classifier, authored data only": ap_auth,
               "Classifier, real + authored (grouped CV)": mp, "Hybrid: rules + real-trained classifier": hp}
    scopes = {"All agreements": [True] * len(real),
              "Indian agreements only": [region[r["source"]] == "india" for r in real]}

    L = ["# Evaluation on labelled real agreements\n",
         f"{len(real)} labelled clauses from {len(by_src)} agreements "
         f"({sum(v == 'india' for v in region.values())} Indian, {sum(v == 'foreign' for v in region.values())} foreign); "
         f"{a.folds}-fold cross-validation grouped by agreement. Labels: {dict(Counter(y))}. "
         f"Extra training data: {len(authored)} authored + {len(synth)} synthetic clauses.\n"]
    for sname, mask in scopes.items():
        yy = [v for v, k in zip(y, mask) if k]
        L += [f"## {sname} ({len(yy)} clauses, {sum(v == RISKY for v in yy)} risky)\n",
              "| System | Acc. | Macro-F1 | Risky P | Risky R | Risky F1 | Fav. F1 | Risky-vs-rest F1 |",
              "|---|---|---|---|---|---|---|---|"]
        for name, p in systems.items():
            m = metrics(yy, [v for v, k in zip(p, mask) if k])
            L.append(f"| {name} | {m['acc']:.2f} | {m['macro_f1']:.2f} | {m['risky_p']:.2f} | {m['risky_r']:.2f} | "
                     f"{m['risky_f1']:.2f} | {m['fav_f1']:.2f} | {m['bin_f1']:.2f} |")
        L.append("")
    L += ["Foreign agreements (tagged automatically; check this list):", ""]
    L += [f"- {s}" for s, v in sorted(region.items()) if v == "foreign"]
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
