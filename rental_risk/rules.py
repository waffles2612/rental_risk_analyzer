"""Rule-based baseline: clause-type keyword scoring + risk pattern matching.

All rules live in rules.json so the Python pipeline and the browser demo stay in sync.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

RULES_PATH = Path(__file__).with_name("rules.json")

RISKY, NEUTRAL, FAVORABLE = "RISKY", "NEUTRAL", "TENANT_FAVORABLE"
OTHER = "OTHER"


@dataclass
class RuleHit:
    rule_id: str
    risk: str
    severity: str
    title: str
    explanation: str
    ask: str = ""
    evidence: str = ""

    def to_dict(self) -> dict:
        return self.__dict__.copy()


@dataclass
class CompiledRule:
    id: str
    types: set
    pattern: re.Pattern
    unless: re.Pattern | None
    value_min: float | None
    value_max: float | None
    risk: str
    severity: str
    title: str
    explanation: str
    ask: str


@dataclass
class RuleBook:
    clause_types: dict
    type_keywords: dict = field(default_factory=dict)
    rules: list = field(default_factory=list)
    severity_weight: dict = field(default_factory=dict)
    risk_labels: dict = field(default_factory=dict)


def _expand(pattern: str, placeholders: dict) -> str:
    for key, value in placeholders.items():
        pattern = pattern.replace("{" + key + "}", value)
    return pattern


@lru_cache(maxsize=4)
def load_rulebook(path: str | None = None) -> RuleBook:
    data = json.loads(Path(path or RULES_PATH).read_text(encoding="utf-8"))
    ph = data["placeholders"]
    book = RuleBook(
        clause_types=data["clause_types"],
        severity_weight=data["severity_weight"],
        risk_labels=data["risk_labels"],
    )
    for ctype, spec in data["clause_types"].items():
        book.type_keywords[ctype] = [(re.compile(p, re.I), w) for p, w in spec["keywords"]]
    for r in data["rules"]:
        book.rules.append(CompiledRule(
            id=r["id"],
            types=set(r["types"]),
            pattern=re.compile(_expand(r["pattern"], ph), re.I),
            unless=re.compile(_expand(r["unless"], ph), re.I) if r.get("unless") else None,
            value_min=r.get("value_min"), value_max=r.get("value_max"),
            risk=r["risk"], severity=r["severity"], title=r["title"],
            explanation=r["explanation"], ask=r.get("ask", ""),
        ))
    return book


_ABBREV = re.compile(r"\b(rs|no|nos|mr|mrs|ms|dr|smt|shri|sri|st|viz|vs|etc|ltd|pvt|approx|sq|ft)\.", re.I)


def normalize(text: str) -> str:
    """Remove periods that aren't sentence ends so clause-level patterns can span them."""
    t = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    t = _ABBREV.sub(lambda m: m.group(1), t)
    t = re.sub(r"\b(i)\.e\.|\b(e)\.g\.", lambda m: (m.group(1) or m.group(2)) + ("e" if m.group(1) else "g"), t, flags=re.I)
    t = re.sub(r"\bp\.\s?([am])\.", r"p\1", t, flags=re.I)  # p.m. / p.a.
    t = re.sub(r"(\d)\.(\d)", r"\1·\2", t)  # protect decimals; converted back in value parsing
    t = re.sub(r"/-", "", t)
    return re.sub(r"\s+", " ", t).strip()


NUMBER_WORDS = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
                "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "fifteen": 15, "twenty": 20, "thirty": 30}


def _num(s: str | None) -> float | None:
    if s is None:
        return None
    w = s.strip().lower()
    if w in NUMBER_WORDS:
        return float(NUMBER_WORDS[w])
    try:
        return float(w.replace("·", ".").replace(",", ""))
    except ValueError:
        return None


def classify_type(text: str, book: RuleBook | None = None) -> tuple[str, dict]:
    """Weighted keyword scoring. Returns (best_type, scores)."""
    book = book or load_rulebook()
    norm = normalize(text)
    # Text before the first colon/full stop often is a heading ("Security Deposit:"); count it twice.
    head = norm[:60].split(":")[0] if ":" in norm[:60] else ""
    scores = {}
    for ctype, kws in book.type_keywords.items():
        s = 0
        for rx, w in kws:
            n = len(rx.findall(norm))
            if n:
                s += w * min(n, 3)
                if head and rx.search(head):
                    s += w * 2
        scores[ctype] = s
    best = max(scores, key=scores.get) if scores else OTHER
    return (best if scores.get(best, 0) > 0 else OTHER), scores


def match_rules(text: str, ctype: str, book: RuleBook | None = None, secondary: str | None = None) -> list[RuleHit]:
    """Apply risk rules relevant to this clause type (plus generic '*' rules)."""
    book = book or load_rulebook()
    norm = normalize(text)
    hits = []
    for r in book.rules:
        if "*" not in r.types and ctype not in r.types and (secondary is None or secondary not in r.types):
            continue
        m = r.pattern.search(norm)
        if not m:
            continue
        if r.unless and r.unless.search(norm):
            continue
        if r.value_min is not None or r.value_max is not None:
            # compare the first captured number of every match against the threshold(s)
            vals = []
            for mm in r.pattern.finditer(norm):
                g = next((x for x in mm.groups() if x), None)
                v = _num(g)
                if v is not None:
                    vals.append(v)
            if not vals:
                continue
            if r.value_min is not None and max(vals) < r.value_min:
                continue
            if r.value_max is not None and min(vals) > r.value_max:
                continue
        hits.append(RuleHit(r.id, r.risk, r.severity, r.title, r.explanation, r.ask,
                            evidence=m.group(0).replace("·", ".")[:160]))
    # de-duplicate same title
    seen, out = set(), []
    for h in hits:
        if h.rule_id not in seen:
            seen.add(h.rule_id)
            out.append(h)
    return out


def risk_from_hits(hits: list) -> str:
    risks = {h["risk"] if isinstance(h, dict) else h.risk for h in hits}
    if RISKY in risks:
        return RISKY
    if FAVORABLE in risks:
        return FAVORABLE
    return NEUTRAL


def second_best_type(scores: dict) -> str | None:
    ranked = sorted(scores.items(), key=lambda kv: -kv[1])
    if len(ranked) > 1 and ranked[1][1] > 0 and ranked[1][1] >= 0.5 * ranked[0][1]:
        return ranked[1][0]
    return None
