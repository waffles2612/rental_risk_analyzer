"""Document-level checks: risks that only show up when clauses are read together.

- deposit size relative to monthly rent
- tenant notice period longer than the landlord's (one-sided termination)
- very short notice to vacate
- important topics missing altogether
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .rules import normalize

WORDNUM = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "fifteen": 15, "twenty": 20, "thirty": 30, "forty-five": 45,
    "forty five": 45, "sixty": 60, "ninety": 90, "a": 1, "an": 1,
}
_UNIT_DAYS = {"day": 1, "week": 7, "month": 30, "year": 365}

_DURATION = re.compile(
    r"\b(\d{1,3}|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty|thirty|forty[- ]five|sixty|ninety|a|an)"
    r"\s*(?:\(\s*\d{1,3}\s*\)\s*)?(?:clear\s+|calendar\s+|working\s+)?(day|week|month|year)s?\b", re.I)
_MONEY = re.compile(r"(?:rs|inr|₹|\$|usd|£|€|rupees)\s*\.?\s*([\d,]+(?:[.·]\d+)?)", re.I)
_T = r"(?:tenants?|lessees?|licensees?)"
_L = r"(?:landlords?|lessors?|licensors?|owners?)"


@dataclass
class DocFinding:
    check_id: str
    risk: str
    severity: str
    title: str
    explanation: str
    ask: str = ""
    clause_indexes: tuple = ()

    def to_dict(self) -> dict:
        d = self.__dict__.copy()
        d["clause_indexes"] = list(self.clause_indexes)
        return d


def parse_durations_days(text: str) -> list[int]:
    out = []
    for m in _DURATION.finditer(text):
        n_raw = m.group(1).lower().replace("-", " ")
        n = int(n_raw) if n_raw.isdigit() else WORDNUM.get(n_raw, WORDNUM.get(n_raw.replace(" ", "-")))
        if n:
            out.append(n * _UNIT_DAYS[m.group(2).lower()])
    return out


def parse_amounts(text: str) -> list[float]:
    vals = []
    for m in _MONEY.finditer(text):
        try:
            v = float(m.group(1).replace(",", "").replace("·", "."))
        except ValueError:
            continue
        if v >= 100:
            vals.append(v)
    return vals


def _months_multiple(text: str) -> float | None:
    m = re.search(r"\b(\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s*(?:\(\s*\d+\s*\)\s*)?months?'?\s*(?:of\s+)?(?:the\s+)?(?:monthly\s+)?(?:rent|rental|license fee)", text, re.I)
    if not m:
        return None
    raw = m.group(1).lower()
    return float(raw) if raw.isdigit() else float(WORDNUM[raw])


def _party_for_notice(sentence: str) -> str | None:
    s = sentence.lower()
    if re.search(r"\b(?:either party|both parties|either of the parties|each party)\b", s):
        return "both"
    if re.search(r"notice\s+(?:from|by|given by|issued by|served by)\s+(?:the\s+)?" + _L, s):
        return "landlord"
    if re.search(r"notice\s+(?:from|by|given by|issued by|served by)\s+(?:the\s+)?" + _T, s):
        return "tenant"
    t = re.search(r"\b" + _T + r"\b", s)
    l = re.search(r"\b" + _L + r"\b", s)
    if t and (not l or t.start() < l.start()):
        return "tenant"
    if l:
        return "landlord"
    return None


def _first_extreme(items: list[tuple[int, int]], fn) -> tuple[int, int]:
    """Extreme duration; on ties the first one found (termination clauses are listed before renewal ones)."""
    best = fn(d for d, _ in items)
    return next(x for x in items if x[0] == best)


def run_document_checks(clauses: list[dict], check_missing: bool = True) -> list[DocFinding]:
    """`clauses` are pipeline result dicts with at least: index, text, clause_type."""
    findings: list[DocFinding] = []
    by_type: dict[str, list[dict]] = {}
    for c in clauses:
        by_type.setdefault(c["clause_type"], []).append(c)

    # 1. Deposit vs rent -------------------------------------------------------
    rent, rent_idx = None, None
    for c in by_type.get("RENT", []) + [c for c in clauses if c["clause_type"] != "RENT"]:
        t = normalize(c["text"])
        if re.search(r"\b(?:rent|license fee)\b", t, re.I) and re.search(r"\bmonth|\bper mensem\b|\bpm\b", t, re.I):
            amts = parse_amounts(t)
            if amts and "deposit" not in t.lower()[:80]:
                rent, rent_idx = amts[0], c["index"]
                break
    for c in by_type.get("DEPOSIT", []):
        t = normalize(c["text"])
        if _months_multiple(t) is not None:
            continue  # "N months' rent" is handled clause-level by DEP_LARGE
        mult, dep = None, None
        if rent:
            amts = parse_amounts(t)
            if amts:
                dep = amts[0]
                mult = dep / rent
        if mult is None:
            continue
        idx = tuple(sorted(i for i in (c["index"], rent_idx) if i))
        if mult > 2.0001:
            findings.append(DocFinding(
                "DOC_DEPOSIT_RATIO", "RISKY", "high" if mult >= 5 else "medium",
                f"Deposit is about {mult:.1f}× the monthly rent",
                f"The security deposit equals roughly {mult:.1f} months of rent. That is a lot of your money held by the landlord, "
                "and it is harder to recover in a dispute. For reference, India's Model Tenancy Act, 2021 suggests a cap of two months' "
                "rent for residential premises (it applies only in states that have adopted it).",
                "Negotiate the deposit down to 2-3 months' rent, or ask for interest on the excess.", idx))
        break

    # 2. Notice periods -----------------------------------------------------------
    tenant_notice, landlord_notice = [], []
    for c in by_type.get("TERMINATION", []) + by_type.get("RENEWAL", []):
        t = normalize(c["text"])
        for sent in re.split(r"(?<=[.;])\s+", t):
            if "notice" not in sent.lower():
                continue
            days = parse_durations_days(sent)
            if not days:
                continue
            party = _party_for_notice(sent)
            d = min(days)
            if party in ("tenant", "both"):
                tenant_notice.append((d, c["index"]))
            if party in ("landlord", "both"):
                landlord_notice.append((d, c["index"]))
    if tenant_notice and landlord_notice:
        tn, ti = _first_extreme(tenant_notice, max)
        ln, li = _first_extreme(landlord_notice, min)
        if tn > ln:
            findings.append(DocFinding(
                "DOC_NOTICE_ASYMMETRY", "RISKY", "high",
                "You must give more notice than the landlord",
                f"You have to give about {tn} days' notice to leave, but the landlord only has to give about {ln} days. "
                "The termination terms are tilted against you.",
                "Ask for the same notice period for both parties.", tuple(sorted({ti, li}))))
    if landlord_notice:
        ln, li = _first_extreme(landlord_notice, min)
        if ln < 30:
            findings.append(DocFinding(
                "DOC_SHORT_NOTICE", "RISKY", "high" if ln <= 15 else "medium",
                f"Only {ln} days' notice to vacate",
                f"The landlord can ask you to leave with only about {ln} days' notice, which is very little time to find a new home.",
                "Ask for at least one month's written notice.", (li,)))

    # 3. Missing topics ---------------------------------------------------------
    expected = {
        "DEPOSIT": ("No security-deposit clause", "Nothing says how much deposit is held, when it is returned, or what can be deducted."),
        "TERMINATION": ("No termination / notice clause", "Nothing says how either side can end the agreement or how much notice is needed."),
        "MAINTENANCE": ("No repairs clause", "Nothing says who pays for repairs. That ambiguity usually ends up costing the tenant."),
    }
    for ctype, (title, expl) in (expected.items() if check_missing else []):
        if not by_type.get(ctype):
            findings.append(DocFinding(f"DOC_MISSING_{ctype}", "RISKY", "low", title, expl,
                                       "Ask for this to be added in writing before signing."))
    return findings
