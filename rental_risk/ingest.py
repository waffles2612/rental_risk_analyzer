"""Step 01 - Ingestion & segmentation: read an agreement and split it into clauses."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Clause:
    index: int
    number: str      # "4", "4.2", "(b)" ... or "" when unnumbered
    heading: str     # e.g. "SECURITY DEPOSIT" when the agreement provides one
    text: str

    @property
    def full_text(self) -> str:
        return f"{self.heading}: {self.text}" if self.heading else self.text


def read_document(path: str | Path) -> str:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        text = "\n".join((p.extract_text() or "") for p in reader.pages)
        if len(text.strip()) < 50:
            raise ValueError(
                f"{path.name} has no extractable text (probably a scanned PDF). Run OCR first, e.g. `ocrmypdf in.pdf out.pdf`.")
        return text
    if suffix == ".docx":
        import docx
        d = docx.Document(str(path))
        parts = [p.text for p in d.paragraphs]
        for table in d.tables:
            for row in table.rows:
                parts.append(" | ".join(c.text for c in row.cells))
        return "\n".join(parts)
    return path.read_text(encoding="utf-8", errors="replace")


# A line starting a new clause: "1.", "1.2", "12)", "(a)", "a)", "iv.", "Clause 3", "Article IV", "Section 2:"
_NUM_START = re.compile(
    r"^\s*(?:"
    r"(?P<kw>(?:clause|article|section)\s+[\dIVXivx]+[.:)]?)"
    r"|(?P<num>\d{1,2}(?:\.\d{1,2}){0,3}[.)]|\d{1,2}(?:\.\d{1,2}){1,3})(?=\s+\S)"
    r"|(?P<alpha>\(?[a-hj-z]\)|\([ivx]{1,4}\)|[ivx]{1,4}[.)])(?=\s+\S)"
    r")\s*", re.I)
# A heading-only line: "SECURITY DEPOSIT", "Termination:", "TERMS AND CONDITIONS"
_HEADING = re.compile(r"^\s*(?:[A-Z][A-Z0-9 &/,'()-]{2,60}|[A-Z][a-zA-Z &/,'-]{2,40}:)\s*$")
_INLINE_HEADING = re.compile(r"^\s*([A-Z][A-Za-z &/'-]{2,40}?)\s*[:–—-]\s+(?=[A-Z])")
_END_OF_TERMS = re.compile(r"^\s*(?:in witness where(?:of|to)|signed (?:sealed )?and delivered|witnesses?\s*[:1]|schedule\s+[a-z0-9]*\s*$)", re.I)
_BOILERPLATE = re.compile(r"^(?:witness(?:es)?|signature|signed|landlord|tenant|lessor|lessee|licensor|licensee|date|place|name)\b.{0,40}$", re.I)


_SMALL = {"and", "of", "the", "to", "for", "in", "on", "by", "with", "a", "an", "&", "or"}


def _is_heading_text(rest: str) -> bool:
    """'Security Deposit', 'TERMINATION', 'Repairs and Maintenance' -> True; 'The Tenant shall give notice of' -> False."""
    words = rest.rstrip(":").split()
    if not words or len(rest) >= 45 or len(words) > 6 or rest.endswith((".", ";", ",")):
        return False
    if words[-1].lower() in _SMALL:
        return False
    return all(w[0].isupper() or w.lower() in _SMALL or not w[0].isalpha() for w in words)


_ABBR = {"mr", "mrs", "ms", "dr", "rs", "no", "nos", "smt", "shri", "sri", "st", "s/o", "d/o", "w/o", "viz", "vs", "etc",
         "ltd", "pvt", "co", "sq", "ft", "approx", "sl", "dt", "ref", "inr", "re", "rd", "opp", "nr", "ph", "e.g", "i.e"}
_BOUNDARY = re.compile(r"[.;]\s+(?=[A-Z(\"'\u201c])")
_PAGE_MARK = re.compile(r"^\s*-\s*\d{1,3}\s*-\s*")
MAX_CLAUSE = 500   # longer blocks (unnumbered pages) are split into sentences
MIN_PIECE = 60     # pieces shorter than this are merged with the next one


def split_long(text: str, max_len: int = MAX_CLAUSE) -> list[str]:
    """Split an over-long block into sentence groups, without breaking on 'Rs.', 'Mr.', initials etc."""
    if len(text) <= max_len:
        return [text]
    pieces, start = [], 0
    for m in _BOUNDARY.finditer(text):
        before = text[start:m.start()].split()
        last = before[-1].lower().strip("(\"'") if before else ""
        if last in _ABBR or len(last) <= 1 or re.fullmatch(r"(?:[a-z]\.)+[a-z]?", last):
            continue
        pieces.append(text[start:m.start() + 1].strip())
        start = m.end()
    pieces.append(text[start:].strip())
    out = []
    for piece in pieces:
        if out and len(out[-1]) < MIN_PIECE:
            out[-1] = out[-1] + " " + piece
        else:
            out.append(piece)
    if len(out) > 1 and len(out[-1]) < MIN_PIECE:
        tail = out.pop()
        out[-1] = out[-1] + " " + tail
    return [x for x in out if x]


def _join_wrapped(lines: list[str]) -> list[str]:
    """Re-join lines that were wrapped mid-sentence (previous line has no end punctuation, next starts lowercase)."""
    out = []
    for ln in lines:
        if out and not re.search(r"[.;:]\s*$", out[-1]) and re.match(r"[a-z0-9(]", ln):
            out[-1] = out[-1] + " " + ln
        else:
            out.append(ln)
    return out


def _looks_like_number_only(line: str) -> bool:
    return bool(re.fullmatch(r"\s*(?:page\s*)?\d+(?:\s*of\s*\d+)?\s*", line, re.I))


def segment(text: str, min_chars: int = 30) -> list[Clause]:
    """Split agreement text into clause-level segments.

    Strategy: (1) numbered/lettered structure, (2) fall back to paragraphs, (3) fall back to sentences.
    Headings ("SECURITY DEPOSIT") are attached to the clause that follows them.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace(" ", " ")
    lines = [_PAGE_MARK.sub("", ln).rstrip() for ln in text.split("\n")]

    starts = sum(1 for ln in lines if _NUM_START.match(ln))
    raw: list[tuple[str, str, str]] = []  # (number, heading, text)

    if starts >= 3:
        cur_num, cur_head, buf, pending_head = "", "", [], ""
        for ln in lines:
            if not ln.strip() or _looks_like_number_only(ln):
                continue
            if _END_OF_TERMS.match(ln):
                break
            m = _NUM_START.match(ln)
            if m:
                if buf:
                    raw.append((cur_num, cur_head, " ".join(buf)))
                rest = ln[m.end():].strip()
                if _is_heading_text(rest):
                    # numbered heading such as "3. Security Deposit": becomes the heading of the clauses under it
                    cur_num, cur_head, buf, pending_head = "", "", [], rest.rstrip(":")
                    continue
                cur_num = (m.group("kw") or m.group("num") or m.group("alpha") or "").strip().rstrip(".:")
                cur_head, buf = pending_head, [rest]
                pending_head = "" if not re.fullmatch(r"\d+\.\d+.*", cur_num) else pending_head
            elif _HEADING.match(ln) and len(ln.strip()) < 60:
                if buf:
                    raw.append((cur_num, cur_head, " ".join(buf)))
                    cur_num, cur_head, buf = "", "", []
                pending_head = ln.strip().rstrip(":")
            else:
                buf.append(ln.strip())
        if buf:
            raw.append((cur_num, cur_head, " ".join(buf)))
    else:
        paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        if len(paras) < 3:
            ls = _join_wrapped([ln.strip() for ln in lines if ln.strip()])
            if len(ls) >= 3 and sum(map(len, ls)) / len(ls) >= 40:  # one clause per line
                paras = ls
            else:  # one block of prose -> sentences
                sentences = re.split(r"(?<=[.;])\s+(?=[A-Z(])", " ".join(paras))
                paras = [s for s in sentences if s.strip()]
        pending_head = ""
        for p in paras:
            p = re.sub(r"^[-*\u2022]\s+", "", " ".join(x.strip() for x in p.split("\n")))
            if _END_OF_TERMS.match(p):
                break
            if _HEADING.match(p) and len(p) < 60:
                pending_head = p.rstrip(":")
                continue
            raw.append(("", pending_head, p))
            pending_head = ""

    clauses: list[Clause] = []
    for num, head, body in raw:
        body = re.sub(r"\s+", " ", body).strip()
        if not head:
            m = _INLINE_HEADING.match(body)
            if m and len(m.group(1).split()) <= 5:
                head, body = m.group(1).strip(), body[m.end():].strip()
        head = head.title() if head.isupper() else head
        for k, piece in enumerate(split_long(body)):
            if len(piece) < min_chars or _BOILERPLATE.match(piece):
                continue
            clauses.append(Clause(len(clauses) + 1, num, head if k == 0 else "", piece))
    return clauses
