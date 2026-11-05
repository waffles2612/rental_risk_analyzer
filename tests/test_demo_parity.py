"""The browser demo re-implements the rule engine in JavaScript. This checks both engines agree.
Skipped when Node.js is not installed. Rebuild the demo first: python demo/build_demo.py"""
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from rental_risk import Analyzer
from rental_risk.ml import load_dataset
from rental_risk.rules import classify_type, match_rules, second_best_type

ROOT = Path(__file__).resolve().parent.parent


@unittest.skipUnless(shutil.which("node"), "node not installed")
class TestDemoParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(["python3", str(ROOT / "demo" / "build_demo.py")], check=True, capture_output=True)
        html = (ROOT / "demo" / "index.html").read_text(encoding="utf-8")
        scripts = re.findall(r"<script>(.*?)</script>", html, re.S)
        cls.core = scripts[0] + scripts[1].split("// ---------- Rendering")[0]

    def run_js(self, tail: str, payload) -> object:
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
            f.write(self.core + f"\nconst INPUT = {json.dumps(payload)};\n" + tail)
        return json.loads(subprocess.check_output(["node", f.name]))

    def test_samples(self):
        texts = [s.read_text(encoding="utf-8") for s in sorted((ROOT / "data" / "sample_agreements").glob("*.txt"))]
        js = self.run_js("console.log(JSON.stringify(INPUT.map(t => { const r = analyze(t); return "
                         "[r.clauses.map(c => [c.clause_type, c.risk, c.findings.map(h => h.rule_id).sort()]), r.doc.map(d => d.check_id), r.summary.rating]; })));", texts)
        a = Analyzer(engine="rules")
        for t, j in zip(texts, js):
            r = a.analyze_text(t)
            py = [[[c["clause_type"], c["risk"], sorted(h["rule_id"] for h in c["findings"])] for c in r["clauses"]],
                  [d["check_id"] for d in r["document_findings"]], r["summary"]["rating"]]
            self.assertEqual(py, j)

    def test_every_labelled_clause(self):
        rows = load_dataset() + load_dataset(ROOT / "data" / "clauses_test.csv")
        texts = [r["text"] for r in rows]
        js = self.run_js("console.log(JSON.stringify(INPUT.map(t => { const [ct, sc] = classifyType(t); "
                         "return [ct, matchRules(t, ct, secondBest(sc)).map(h => h.rule_id).sort()]; })));", texts)
        for t, j in zip(texts, js):
            ct, sc = classify_type(t)
            py = [ct, sorted(h.rule_id for h in match_rules(t, ct, secondary=second_best_type(sc)))]
            self.assertEqual(py, j, t)


if __name__ == "__main__":
    unittest.main()
