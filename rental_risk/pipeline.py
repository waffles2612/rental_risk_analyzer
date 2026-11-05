"""End-to-end pipeline: 01 segment -> 02 classify -> 03 assess risk -> 04 flag & explain."""
from __future__ import annotations

import re
from pathlib import Path

from .doccheck import parse_amounts, parse_durations_days, run_document_checks
from .ingest import Clause, read_document, segment
from .rules import (FAVORABLE, NEUTRAL, RISKY, classify_type, load_rulebook, match_rules,
                    normalize, risk_from_hits, second_best_type)

# Model may overrule a rule-level "tenant-favourable" verdict only when fairly sure the clause is risky.
HYBRID_OVERRIDE_FAVORABLE = 0.6


def hybrid_risk(rule_risk: str, ml_risk: str, p_risky: float) -> str:
    """Rules first (they come with explanations); the model fills the gaps.
    A rule-detected risk is never dropped: a missed risk costs the tenant more than a false alarm."""
    if rule_risk == RISKY:
        return RISKY
    if rule_risk == FAVORABLE:
        return RISKY if p_risky >= HYBRID_OVERRIDE_FAVORABLE else FAVORABLE
    return ml_risk


SEV_ORDER = {"high": 3, "medium": 2, "low": 1, "": 0}
ENGINES = ("rules", "ml", "hybrid", "llm")


def _key_facts(text: str) -> list[str]:
    t = normalize(text)
    facts = []
    for d in sorted(set(parse_durations_days(t))):
        facts.append(f"{d // 30} month(s)" if d >= 30 and d % 30 == 0 else f"{d} day(s)")
    for a in parse_amounts(t)[:3]:
        facts.append(f"₹{a:,.0f}")
    for p in re.findall(r"(\d+(?:[.·]\d+)?)\s*(?:%|percent|per cent)", t, re.I)[:3]:
        facts.append(p.replace("·", ".") + "%")
    return facts[:6]


def explain(risk: str, hits: list[dict], facts: list[str], model_terms: list[str] | None = None) -> tuple[str, str, str]:
    """Step 04: turn findings into (severity, plain-English explanation, suggested ask)."""
    risky = sorted([h for h in hits if h["risk"] == RISKY], key=lambda h: -SEV_ORDER[h["severity"]])
    fav = [h for h in hits if h["risk"] == FAVORABLE]
    if risk == RISKY:
        if risky:
            parts = [h["explanation"] for h in risky[:2]]
            sev = risky[0]["severity"]
            ask = risky[0].get("ask", "")
        else:  # flagged by the model only
            terms = ", ".join(f"“{t}”" for t in (model_terms or [])[:4])
            parts = [("The trained model rates this clause as risky because its wording resembles risky clauses in the training data"
                      + (f" (driven by {terms})." if terms else ".")) + " Read it carefully and ask what each obligation means for you in practice."]
            sev, ask = "medium", "Ask the landlord to clarify or narrow this clause in writing."
        if facts:
            parts.append("Key numbers: " + ", ".join(facts) + ".")
        return sev, " ".join(parts), ask
    if risk == FAVORABLE:
        return "low", " ".join(h["explanation"] for h in fav[:2]) or "This clause adds protection for you as the tenant.", ""
    return "", "Standard clause; no risk indicators found.", ""


class Analyzer:
    def __init__(self, engine: str = "auto", model_path: str | Path | None = None):
        self.book = load_rulebook()
        self.model = None
        self.llm = None
        if engine == "auto":
            from .ml import DEFAULT_MODEL
            engine = "hybrid" if Path(model_path or DEFAULT_MODEL).exists() else "rules"
        if engine not in ENGINES:
            raise ValueError(f"engine must be one of {ENGINES} or 'auto'")
        self.engine = engine
        if engine in ("ml", "hybrid"):
            from .ml import DEFAULT_MODEL, ClauseModel
            p = Path(model_path or DEFAULT_MODEL)
            if not p.exists():
                raise FileNotFoundError(f"No trained model at {p}. Run: python -m rental_risk train")
            self.model = ClauseModel.load(p)
        if engine == "llm":
            from .llm import LLMEngine
            self.llm = LLMEngine()

    # --- per-clause ------------------------------------------------------------
    def _analyse_clause(self, c: Clause) -> dict:
        text = c.full_text
        rtype, scores = classify_type(text, self.book)
        detail = {}
        ctype = rtype
        ml = None
        if self.model is not None:
            ml = self.model.predict(text)
            detail = {"ml_type": ml["clause_type"], "ml_type_conf": round(ml["type_confidence"], 3),
                      "ml_risk": ml["risk"], "ml_risk_conf": round(ml["risk_confidence"], 3),
                      "rule_type": rtype}
            # trust the model's type when it is confident, otherwise keep the keyword type
            if self.engine == "ml" or (rtype == "OTHER" or ml["type_confidence"] >= 0.5):
                ctype = ml["clause_type"]
        hits = [h.to_dict() for h in match_rules(text, ctype, self.book, secondary=second_best_type(scores) if ctype == rtype else rtype)]
        rule_risk = risk_from_hits(hits)
        if self.engine == "rules":
            risk = rule_risk
        elif self.engine == "ml":
            risk = ml["risk"]
        else:
            risk = hybrid_risk(rule_risk, ml["risk"], ml["risk_probs"].get(RISKY, 0.0))
        facts = _key_facts(text)
        sev, expl, ask = explain(risk, hits, facts, ml["top_terms"] if ml else None)
        return {
            "index": c.index, "number": c.number, "heading": c.heading, "text": c.text,
            "clause_type": ctype, "type_label": self.book.clause_types.get(ctype, {}).get("label", "Other"),
            "risk": risk, "severity": sev, "findings": hits, "explanation": expl, "ask": ask,
            "key_facts": facts, "detail": detail,
        }

    # --- document ---------------------------------------------------------------
    def analyze_text(self, text: str, title: str = "Rental agreement") -> dict:
        clauses = segment(text)
        if self.engine == "llm":
            results = self._analyse_llm(clauses)
        else:
            results = [self._analyse_clause(c) for c in clauses]
            results = self._cross_clause_cleanup(results)
        doc_findings = [f.to_dict() for f in run_document_checks(results)]
        doc_findings = fold_doc_findings(results, doc_findings, recompute=self.engine != "llm")
        return {"title": title, "engine": self.engine, "clauses": results,
                "document_findings": doc_findings, "summary": summarize(results, doc_findings, self.book.severity_weight)}

    def _cross_clause_cleanup(self, results: list[dict]) -> list[dict]:
        """A deposit clause without a deadline is fine if another clause sets one."""
        has_deadline = any(h["rule_id"] == "DEP_TIMELINE" for r in results for h in r["findings"])
        if not has_deadline:
            return results
        for r in results:
            before = len(r["findings"])
            r["findings"] = [h for h in r["findings"] if h["rule_id"] != "DEP_NO_TIMELINE"]
            if len(r["findings"]) != before and self.engine == "rules":
                r["risk"] = risk_from_hits(r["findings"])
                r["severity"], r["explanation"], r["ask"] = explain(r["risk"], r["findings"], r["key_facts"])
        return results

    def analyze_file(self, path: str | Path) -> dict:
        path = Path(path)
        return self.analyze_text(read_document(path), title=path.stem.replace("_", " ").replace("-", " "))

    def _analyse_llm(self, clauses: list[Clause]) -> list[dict]:
        payload = [{"index": c.index, "text": c.full_text} for c in clauses]
        out = self.llm.analyse(payload)
        results = []
        for c in clauses:
            r = out.get(c.index, {"clause_type": "OTHER", "risk": NEUTRAL, "severity": "low", "explanation": "", "ask": ""})
            hits = [h.to_dict() for h in match_rules(c.full_text, r["clause_type"], self.book)]
            results.append({
                "index": c.index, "number": c.number, "heading": c.heading, "text": c.text,
                "clause_type": r["clause_type"], "type_label": self.book.clause_types.get(r["clause_type"], {}).get("label", "Other"),
                "risk": r["risk"], "severity": r["severity"] if r["risk"] == RISKY else "",
                "findings": hits, "explanation": r["explanation"] or "Standard clause; no risk indicators found.",
                "ask": r["ask"], "key_facts": _key_facts(c.full_text), "detail": {"llm_model": self.llm.model},
            })
        return results


FOLD_INTO_CLAUSES = {"DOC_NOTICE_ASYMMETRY", "DOC_DEPOSIT_RATIO", "DOC_SHORT_NOTICE"}


def fold_doc_findings(results: list[dict], doc_findings: list[dict], recompute: bool = True) -> list[dict]:
    """Attach cross-clause findings to the clauses they point at, so those clauses are flagged too.
    Drops a document finding that only repeats a clause-level hit (e.g. short notice)."""
    by_idx = {r["index"]: r for r in results}
    kept = []
    for f in doc_findings:
        if f["check_id"] == "DOC_SHORT_NOTICE" and any(h["rule_id"] in ("TERM_SHORT_NOTICE", "TERM_IMMEDIATE_VACATE")
                                                       for r in results for h in r["findings"]):
            continue
        kept.append(f)
        if f["check_id"] not in FOLD_INTO_CLAUSES:
            continue
        for i in f["clause_indexes"]:
            r = by_idx.get(i)
            if r is None or any(h["rule_id"] == f["check_id"] for h in r["findings"]):
                continue
            if f["check_id"] == "DOC_DEPOSIT_RATIO" and r["clause_type"] != "DEPOSIT":
                continue
            r["findings"].append({"rule_id": f["check_id"], "risk": f["risk"], "severity": f["severity"], "title": f["title"],
                                  "explanation": f["explanation"], "ask": f.get("ask", ""), "evidence": ""})
            if recompute:
                r["risk"] = RISKY
                r["severity"], r["explanation"], r["ask"] = explain(RISKY, r["findings"], r["key_facts"])
    return kept


def summarize(clauses: list[dict], doc_findings: list[dict], weights: dict) -> dict:
    counts = {RISKY: 0, NEUTRAL: 0, FAVORABLE: 0}
    sev = {"high": 0, "medium": 0, "low": 0}
    for c in clauses:
        counts[c["risk"]] = counts.get(c["risk"], 0) + 1
        if c["risk"] == RISKY:
            sev[c["severity"] or "medium"] += 1
    for f in doc_findings:
        if f["risk"] == RISKY:
            sev[f["severity"]] += 1
    score = sum(weights[k] * v for k, v in sev.items())
    rating = "High" if sev["high"] >= 3 or score >= 14 else "Moderate" if score >= 5 else "Low"
    return {"clauses": len(clauses), "risk_counts": counts, "severity_counts": sev, "score": score, "rating": rating}
