"""Upgrade path 2: few-shot LLM classification + explanation.

Requires `pip install anthropic` and ANTHROPIC_API_KEY. The whole agreement is sent in one call so the
model can use cross-clause context. Few-shot examples come from the labelled dataset.
"""
from __future__ import annotations

import json
import os
import re

from .ml import DEFAULT_DATA, load_dataset

CLAUSE_TYPES = ["RENT", "DEPOSIT", "TERMINATION", "RENEWAL", "MAINTENANCE", "PENALTY", "ENTRY", "LIABILITY", "USE", "OTHER"]
RISKS = ["RISKY", "NEUTRAL", "TENANT_FAVORABLE"]
DEFAULT_LLM_MODEL = os.environ.get("RENTAL_RISK_LLM_MODEL", "claude-sonnet-5-5")

SYSTEM = f"""You review residential rental / leave-and-licence agreements from the TENANT's point of view.
For every numbered clause you are given, return:
- clause_type: one of {CLAUSE_TYPES}
- risk: one of {RISKS}. RISKY = shifts cost, liability or control onto the tenant beyond what is usual, or is one-sided/vague in a way that can hurt the tenant. TENANT_FAVORABLE = adds protection for the tenant beyond the usual. Otherwise NEUTRAL.
- severity: "high", "medium" or "low" (only meaningful for RISKY; use "low" otherwise)
- explanation: 1-2 plain-English sentences a non-lawyer understands. Say what could happen to the tenant, using the clause's own numbers.
- ask: for RISKY clauses, one concrete change the tenant can request; otherwise "".
Also consider the agreement as a whole (e.g. deposit vs rent, unequal notice periods).
Do not give legal advice beyond this; never invent facts that are not in the text.
Reply with ONLY a JSON array, one object per clause, each including its "index"."""


def _few_shot(n_per_label: int = 2) -> str:
    try:
        rows = load_dataset(DEFAULT_DATA)
    except FileNotFoundError:
        return ""
    picked = []
    for label in RISKS:
        picked += [r for r in rows if r["risk"] == label][:n_per_label]
    lines = [f'- "{r["text"]}" -> clause_type={r["clause_type"]}, risk={r["risk"]}' for r in picked]
    return "Labelled examples:\n" + "\n".join(lines)


class LLMEngine:
    def __init__(self, model: str = DEFAULT_LLM_MODEL):
        try:
            import anthropic
        except ImportError as e:
            raise RuntimeError("The LLM engine needs the anthropic SDK: pip install anthropic") from e
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError("Set ANTHROPIC_API_KEY to use the LLM engine.")
        self.client = anthropic.Anthropic()
        self.model = model

    def analyse(self, clauses: list[dict]) -> dict[int, dict]:
        body = "\n".join(f"[{c['index']}] {c['text']}" for c in clauses)
        msg = self.client.messages.create(
            model=self.model,
            max_tokens=8000,
            system=SYSTEM,
            messages=[{"role": "user", "content": f"{_few_shot()}\n\nAgreement clauses:\n{body}"}],
        )
        text = "".join(getattr(b, "text", "") for b in msg.content)
        m = re.search(r"\[.*\]", text, re.S)
        items = json.loads(m.group(0) if m else text)
        out = {}
        for it in items:
            idx = int(it.get("index", -1))
            out[idx] = {
                "clause_type": it.get("clause_type") if it.get("clause_type") in CLAUSE_TYPES else "OTHER",
                "risk": it.get("risk") if it.get("risk") in RISKS else "NEUTRAL",
                "severity": it.get("severity", "low"),
                "explanation": it.get("explanation", ""),
                "ask": it.get("ask", ""),
            }
        return out
