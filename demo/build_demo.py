"""Build demo/index.html from template.html + the shared rules.json + sample agreements.
Run after editing rules: python demo/build_demo.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = [
    ("Risky leave & licence", "leave_and_license_risky.txt"),
    ("Balanced lease", "residential_lease_balanced.txt"),
    ("Room rental (unnumbered)", "unnumbered_room_rental.txt"),
    ("Clause list (one per line)", "clause_list.txt"),
]


def standalone(fragment: str) -> str:
    """Wrap the fragment as a full HTML document: UTF-8 declared, standards mode, mobile viewport."""
    head_end = fragment.index("<style>")
    head, body = fragment[:head_end], fragment[head_end:]
    style_end = body.index("</style>") + len("</style>")
    style, body = body[:style_end], body[style_end:]
    return ("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">\n"
            + head + "<style>html,body{margin:0}[hidden]{display:none!important}</style>\n" + style + "\n</head>\n<body>\n" + body.strip() + "\n</body>\n</html>\n")


def main():
    rules = json.loads((ROOT / "rental_risk" / "rules.json").read_text(encoding="utf-8"))
    samples = [{"name": n, "text": (ROOT / "data" / "sample_agreements" / f).read_text(encoding="utf-8")} for n, f in SAMPLES]
    engine = (ROOT / "demo" / "engine.js").read_text(encoding="utf-8")
    dump = lambda o: json.dumps(o, ensure_ascii=True).replace("</", "<\\/")
    for template, out_name in [("template.html", "index.html"), ("dashboard_template.html", "dashboard.html")]:
        src = ROOT / "demo" / template
        if not src.exists():
            continue
        html = src.read_text(encoding="utf-8")
        html = html.replace("/*__RULES__*/null", dump(rules)).replace("/*__SAMPLES__*/null", dump(samples))
        html = html.replace("/*__ENGINE__*/", engine)
        # 1) artifact source (a page fragment; the hosting site adds <html>/<head>)
        frag = ROOT / "demo" / "artifact" / out_name
        frag.parent.mkdir(exist_ok=True)
        frag.write_text(html, encoding="utf-8")
        # 2) standalone page you can double-click and open offline
        out = ROOT / "demo" / out_name
        out.write_text(standalone(html), encoding="utf-8")
        print(f"wrote {out} ({len(html) // 1024} KB, {len(rules['rules'])} rules)")
        if out_name == "dashboard.html":
            (ROOT / "Open_Dashboard.html").write_text(standalone(html), encoding="utf-8")


if __name__ == "__main__":
    main()
