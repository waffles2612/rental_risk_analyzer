"""Reports: self-contained HTML (highlighted clauses), Markdown, JSON."""
from __future__ import annotations

import html
import json
import re

RISK_LABEL = {"RISKY": "Risky", "NEUTRAL": "Neutral", "TENANT_FAVORABLE": "Tenant-favourable"}


def to_json(report: dict) -> str:
    return json.dumps(report, indent=2, ensure_ascii=False)


def _highlight(text: str, findings: list[dict]) -> str:
    """Escape text and wrap rule evidence in <mark>. Evidence was matched on normalised text, so match loosely."""
    out = html.escape(text)
    for f in findings:
        ev = (f.get("evidence") or "").strip()
        if len(ev) < 4:
            continue
        words = [re.escape(html.escape(w)) for w in ev.split()]
        rx = re.compile(r"[\s.]*".join(words), re.I)
        cls = "mr" if f["risk"] == "RISKY" else "mf"
        out, _ = rx.subn(lambda m: f'<mark class="{cls}">{m.group(0)}</mark>', out, count=1)
    return out


def to_markdown(report: dict) -> str:
    s = report["summary"]
    lines = [f"# Risk report: {report['title']}", "",
             f"**Overall risk: {s['rating']}** · {s['clauses']} clauses · "
             f"{s['risk_counts']['RISKY']} risky, {s['risk_counts']['TENANT_FAVORABLE']} tenant-favourable · engine: {report['engine']}", ""]
    if report["document_findings"]:
        lines += ["## Whole-agreement findings", ""]
        for f in report["document_findings"]:
            lines.append(f"- **{f['title']}** ({f['severity']}). {f['explanation']}" + (f" *Ask for:* {f['ask']}" if f.get("ask") else ""))
        lines.append("")
    lines += ["## Flagged clauses", ""]
    for c in report["clauses"]:
        if c["risk"] != "RISKY":
            continue
        ref = f"Clause {c['number']}" if c["number"] else f"Segment {c['index']}"
        lines += [f"### {ref} · {c['type_label']} · {c['severity']}", "", f"> {c['text']}", "",
                  c["explanation"], ""]
        if c["ask"]:
            lines += [f"*Ask for:* {c['ask']}", ""]
    lines += ["---", "Automated screening, not legal advice. Have important agreements reviewed by a lawyer."]
    return "\n".join(lines)


def to_html(report: dict) -> str:
    s = report["summary"]
    e = html.escape
    rating_cls = {"High": "r-high", "Moderate": "r-mod", "Low": "r-low"}[s["rating"]]
    doc_items = "".join(
        f'<li class="df sev-{e(f["severity"])}"><strong>{e(f["title"])}</strong><span class="sev">{e(f["severity"])}</span>'
        f'<p>{e(f["explanation"])}</p>' + (f'<p class="ask">Ask for: {e(f["ask"])}</p>' if f.get("ask") else "")
        + (f'<p class="refs">See segment(s) {", ".join(str(i) for i in f["clause_indexes"])}</p>' if f.get("clause_indexes") else "")
        + "</li>" for f in report["document_findings"])
    cards = []
    for c in report["clauses"]:
        ref = f"Clause {c['number']}" if c["number"] else f"Segment {c['index']}"
        badge = RISK_LABEL[c["risk"]] + (f" · {c['severity']}" if c["risk"] == "RISKY" and c["severity"] else "")
        tags = "".join(f'<span class="tag t-{"r" if f["risk"]=="RISKY" else "f"}">{e(f["title"])}</span>' for f in c["findings"])
        cards.append(
            f'<article class="clause k-{c["risk"]}" id="c{c["index"]}" data-risk="{c["risk"]}">'
            f'<header><span class="ref">{e(ref)}</span><span class="type">{e(c["type_label"])}</span>'
            + (f'<span class="head">{e(c["heading"])}</span>' if c["heading"] else "")
            + f'<span class="badge b-{c["risk"]}">{e(badge)}</span></header>'
            f'<p class="text">{_highlight(c["text"], c["findings"])}</p>'
            + (f'<div class="tags">{tags}</div>' if tags else "")
            + (f'<div class="expl"><p>{e(c["explanation"])}</p>' + (f'<p class="ask">Ask for: {e(c["ask"])}</p>' if c["ask"] else "") + "</div>"
               if c["risk"] != "NEUTRAL" else "")
            + "</article>")
    rc = s["risk_counts"]
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Risk report · {e(report['title'])}</title>
<style>
:root{{--bg:#f6f5f1;--card:#fff;--ink:#1d2330;--mute:#5d6577;--line:#e3e1da;--red:#b42318;--redbg:#fde8e6;--amber:#9a6700;--green:#1a7f37;--greenbg:#e6f4ea;--gold:#e0b100;--markr:#ffd8d3;--markf:#cdeccf}}
@media (prefers-color-scheme:dark){{:root{{--bg:#0d1420;--card:#152031;--ink:#e8ebf1;--mute:#9aa4b6;--line:#26324a;--red:#ff8a80;--redbg:#3a1d22;--amber:#f0c060;--green:#7fd99a;--greenbg:#173326;--markr:#5a2a2a;--markf:#1f4a2e}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}}
.wrap{{max-width:920px;margin:0 auto;padding:28px 16px 60px}}
h1{{font-size:26px;margin:0 0 4px}}.sub{{color:var(--mute);margin:0 0 20px}}
.summary{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-bottom:22px}}
.stat{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px}}.stat b{{display:block;font-size:24px}}.stat span{{color:var(--mute);font-size:13px}}
.r-high b{{color:var(--red)}}.r-mod b{{color:var(--amber)}}.r-low b{{color:var(--green)}}
h2{{font-size:17px;margin:26px 0 10px}}
.docf{{list-style:none;padding:0;margin:0;display:grid;gap:8px}}.df{{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--red);border-radius:8px;padding:10px 14px}}
.df.sev-low{{border-left-color:var(--amber)}}.df p{{margin:4px 0 0}}.sev{{margin-left:8px;font-size:12px;color:var(--mute);text-transform:uppercase}}
.refs{{font-size:13px;color:var(--mute)}}.ask{{font-weight:600}}
.filters{{display:flex;gap:6px;flex-wrap:wrap;margin:8px 0 12px}}.filters button{{border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:999px;padding:5px 12px;cursor:pointer;font:inherit;font-size:13px}}
.filters button[aria-pressed=true]{{background:var(--ink);color:var(--bg)}}
.clause{{background:var(--card);border:1px solid var(--line);border-left:5px solid var(--line);border-radius:10px;padding:12px 16px;margin-bottom:10px}}
.k-RISKY{{border-left-color:var(--red)}}.k-TENANT_FAVORABLE{{border-left-color:var(--green)}}
.clause header{{display:flex;flex-wrap:wrap;gap:8px;align-items:center;font-size:13px}}.ref{{font-weight:700}}.type,.head{{color:var(--mute)}}
.badge{{margin-left:auto;border-radius:999px;padding:2px 10px;font-weight:600;font-size:12px}}.b-RISKY{{background:var(--redbg);color:var(--red)}}.b-TENANT_FAVORABLE{{background:var(--greenbg);color:var(--green)}}.b-NEUTRAL{{border:1px solid var(--line);color:var(--mute)}}
.text{{margin:8px 0}}mark{{border-radius:3px;padding:0 2px;color:inherit}}mark.mr{{background:var(--markr)}}mark.mf{{background:var(--markf)}}
.tags{{display:flex;gap:6px;flex-wrap:wrap}}.tag{{font-size:12px;border-radius:6px;padding:2px 8px}}.t-r{{background:var(--redbg);color:var(--red)}}.t-f{{background:var(--greenbg);color:var(--green)}}
.expl{{margin-top:8px;padding-top:8px;border-top:1px dashed var(--line)}}.expl p{{margin:2px 0}}
footer{{margin-top:30px;color:var(--mute);font-size:13px}}
</style></head><body><div class="wrap">
<h1>{e(report['title'])}</h1><p class="sub">Automated risk-clause screening · engine: {e(report['engine'])}</p>
<div class="summary"><div class="stat {rating_cls}"><b>{e(s['rating'])}</b><span>overall risk (score {s['score']})</span></div>
<div class="stat"><b>{rc['RISKY']}</b><span>risky clauses ({s['severity_counts']['high']} high)</span></div>
<div class="stat"><b>{rc['TENANT_FAVORABLE']}</b><span>tenant-favourable</span></div>
<div class="stat"><b>{s['clauses']}</b><span>clauses reviewed</span></div></div>
{f'<h2>Whole-agreement findings</h2><ul class="docf">{doc_items}</ul>' if doc_items else ''}
<h2>Clause by clause</h2>
<div class="filters" role="group"><button data-f="all" aria-pressed="true">All</button><button data-f="RISKY" aria-pressed="false">Risky</button><button data-f="TENANT_FAVORABLE" aria-pressed="false">Tenant-favourable</button><button data-f="NEUTRAL" aria-pressed="false">Neutral</button></div>
{''.join(cards)}
<footer>Automated screening, not legal advice. Have important agreements reviewed by a lawyer before signing.</footer>
</div><script>
document.querySelectorAll('.filters button').forEach(b=>b.onclick=()=>{{document.querySelectorAll('.filters button').forEach(x=>x.setAttribute('aria-pressed',x===b));
document.querySelectorAll('.clause').forEach(c=>c.style.display=(b.dataset.f==='all'||c.dataset.risk===b.dataset.f)?'':'none')}});
</script></body></html>"""
