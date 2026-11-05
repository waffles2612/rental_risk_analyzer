"""Upgrade path 1: a trained classifier (TF-IDF + logistic regression).

Small, fast and explainable: each prediction can name the words that pushed it towards "risky".
Swap `build_model()` for a fine-tuned transformer later without touching the rest of the pipeline.
"""
from __future__ import annotations

import csv
from pathlib import Path

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline

from .rules import normalize

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA = ROOT / "data" / "clauses.csv"
DEFAULT_MODEL = ROOT / "models" / "clause_model.joblib"


CLAUSE_TYPES = {"RENT", "DEPOSIT", "TERMINATION", "RENEWAL", "MAINTENANCE", "PENALTY", "ENTRY", "LIABILITY", "USE", "OTHER"}
RISK_LABELS = {"RISKY", "NEUTRAL", "TENANT_FAVORABLE"}
_RISK_ALIASES = {"RISK": "RISKY", "FAVORABLE": "TENANT_FAVORABLE", "FAVOURABLE": "TENANT_FAVORABLE",
                 "TENANT_FAVOURABLE": "TENANT_FAVORABLE", "TENANT-FAVOURABLE": "TENANT_FAVORABLE",
                 "TENANT-FAVORABLE": "TENANT_FAVORABLE", "SAFE": "NEUTRAL"}


def _csv_paths(paths) -> list[Path]:
    if isinstance(paths, (str, Path)):
        paths = [paths]
    out = []
    for p in paths:
        p = Path(p)
        out += sorted([*p.glob("*.csv"), *p.glob("*.xlsx")]) if p.is_dir() else [p]
    return [x for x in out if not x.name.startswith("~$")]  # skip Excel lock files


def _read_rows(p: Path):
    """Yield (line_number, row_dict) from a .csv or .xlsx (first sheet, header in row 1)."""
    if p.suffix.lower() == ".xlsx":
        from openpyxl import load_workbook
        wb = load_workbook(p, read_only=True, data_only=True)
        try:
            it = wb.worksheets[0].iter_rows(values_only=True)
            header = [str(h or "").strip() for h in next(it, [])]
            for n, vals in enumerate(it, start=2):
                yield n, {h: ("" if v is None else str(v)) for h, v in zip(header, vals)}
        finally:
            wb.close()  # read-only mode holds the file open; Windows can't delete it otherwise
        return
    with open(p, newline="", encoding="utf-8-sig") as f:
        yield from enumerate(csv.DictReader(f), start=2)


def load_dataset(path=DEFAULT_DATA, strict: bool = False, report: bool = False) -> list[dict]:
    """Load one or more labelled CSVs (or folders of them).

    Needs columns `text`, `clause_type`, `risk`. Rows with an empty or unknown label are skipped
    (with a warning when report=True), so a half-labelled sheet can still be used.
    Duplicate clause texts are kept once."""
    rows, seen, problems = [], set(), []
    for p in _csv_paths(path):
        if True:
            for n, r in _read_rows(p):
                text = (r.get("text") or "").strip()
                if not text:
                    continue
                ctype = (r.get("clause_type") or "").strip().upper()
                risk = (r.get("risk") or "").strip().upper().replace(" ", "_")
                risk = _RISK_ALIASES.get(risk, risk)
                if ctype not in CLAUSE_TYPES or risk not in RISK_LABELS:
                    if ctype or risk:
                        problems.append(f"{p.name} line {n}: clause_type={ctype or '(empty)'} risk={risk or '(empty)'}")
                    continue
                key = " ".join(text.lower().split())
                if key in seen:
                    continue
                seen.add(key)
                rows.append({**r, "text": text, "clause_type": ctype, "risk": risk, "source": r.get("source") or p.stem})
    if problems and (strict or report):
        msg = f"Skipped {len(problems)} row(s) with invalid labels:\n  " + "\n  ".join(problems[:20])
        if strict:
            raise ValueError(msg)
        print(msg)
    return rows


def _prep(s: str) -> str:
    return normalize(s).lower()


def build_model() -> Pipeline:
    features = FeatureUnion([
        ("word", TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True, preprocessor=_prep)),
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=2, sublinear_tf=True, preprocessor=_prep)),
    ])
    return Pipeline([("features", features),
                     ("clf", LogisticRegression(max_iter=3000, C=8.0, class_weight="balanced"))])


class ClauseModel:
    def __init__(self, type_model: Pipeline, risk_model: Pipeline):
        self.type_model = type_model
        self.risk_model = risk_model

    @classmethod
    def train(cls, rows: list[dict]) -> "ClauseModel":
        texts = [r["text"] for r in rows]
        tm = build_model().fit(texts, [r["clause_type"] for r in rows])
        rm = build_model().fit(texts, [r["risk"] for r in rows])
        return cls(tm, rm)

    def save(self, path: str | Path = DEFAULT_MODEL) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"type": self.type_model, "risk": self.risk_model}, path)
        return path

    @classmethod
    def load(cls, path: str | Path = DEFAULT_MODEL) -> "ClauseModel":
        d = joblib.load(path)
        return cls(d["type"], d["risk"])

    def predict(self, text: str) -> dict:
        tp = self.type_model.predict_proba([text])[0]
        rp = self.risk_model.predict_proba([text])[0]
        t_classes, r_classes = self.type_model.classes_, self.risk_model.classes_
        risk = r_classes[int(np.argmax(rp))]
        return {
            "clause_type": t_classes[int(np.argmax(tp))],
            "type_confidence": float(tp.max()),
            "risk": risk,
            "risk_confidence": float(rp.max()),
            "risk_probs": {c: float(p) for c, p in zip(r_classes, rp)},
            "top_terms": self.top_terms(text, "RISKY") if "RISKY" in r_classes else [],
        }

    def top_terms(self, text: str, label: str, k: int = 5) -> list[str]:
        """Words/phrases in this clause that pushed the model most towards `label`."""
        feats: FeatureUnion = self.risk_model.named_steps["features"]
        clf: LogisticRegression = self.risk_model.named_steps["clf"]
        x = feats.transform([text])
        classes = list(clf.classes_)
        coef = clf.coef_[classes.index(label)] if clf.coef_.shape[0] > 1 else clf.coef_[0]
        contrib = x.multiply(coef).toarray()[0]
        names = feats.get_feature_names_out()
        order = np.argsort(-contrib)
        out = []
        for i in order:
            if contrib[i] <= 0 or len(out) >= k:
                break
            if names[i].startswith("word__"):
                term = names[i][6:]
                if not any(term in o or o in term for o in out):
                    out.append(term)
        return out
