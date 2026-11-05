"""Run: python -m unittest discover -s tests -v"""
import json
import re
import tempfile
import unittest
from pathlib import Path

from rental_risk import Analyzer, segment
from rental_risk.doccheck import parse_amounts, parse_durations_days, run_document_checks
from rental_risk.ml import ClauseModel, load_dataset
from rental_risk.rules import RULES_PATH, classify_type, match_rules

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "data" / "sample_agreements"


def ids(text, ctype):
    return {h.rule_id for h in match_rules(text, ctype)}


class TestSegmentation(unittest.TestCase):
    def test_numbered(self):
        cl = segment((SAMPLES / "leave_and_license_risky.txt").read_text())
        self.assertGreaterEqual(len(cl), 18)
        self.assertEqual(cl[1].number, "1")
        self.assertEqual(cl[3].heading, "Security Deposit")
        self.assertFalse(any("Witness" in c.text for c in cl))

    def test_decimal_numbering_and_headings(self):
        cl = segment((SAMPLES / "residential_lease_balanced.txt").read_text())
        self.assertIn("2.3", [c.number for c in cl])
        self.assertEqual(next(c for c in cl if c.number == "3.1").heading, "Security Deposit")

    def test_unnumbered_paragraphs(self):
        cl = segment((SAMPLES / "unnumbered_room_rental.txt").read_text())
        self.assertGreaterEqual(len(cl), 7)
        self.assertEqual(cl[1].heading, "Rent")

    def test_no_false_split_on_wrapped_numbers(self):
        text = "1. The Tenant shall give notice of\n30 days before leaving.\n2. Rent is due monthly on the fifth day.\n3. The deposit is refundable on vacating the flat."
        cl = segment(text)
        self.assertEqual(len(cl), 3)
        self.assertIn("30 days", cl[0].text)


class TestRules(unittest.TestCase):
    def test_rules_json_is_js_compatible(self):
        data = json.loads(RULES_PATH.read_text())
        for r in data["rules"]:
            for key in ("pattern", "unless"):
                p = r.get(key, "")
                self.assertNotRegex(p, r"\(\?<[=!]", f"{r['id']} uses lookbehind")
                self.assertNotIn("(?P<", p, f"{r['id']} uses Python named group")

    def test_classify(self):
        self.assertEqual(classify_type("Security Deposit: Rs. 50,000 refundable on vacating.")[0], "DEPOSIT")
        self.assertEqual(classify_type("The Landlord may enter and inspect the premises.")[0], "ENTRY")
        self.assertEqual(classify_type("Hello world")[0], "OTHER")

    def test_risky_patterns(self):
        self.assertIn("TERM_LANDLORD_ANYTIME", ids("The Landlord may terminate at any time without assigning any reason.", "TERMINATION"))
        self.assertIn("REN_AUTO", ids("This agreement shall stand extended for eleven months unless notice is given.", "RENEWAL"))
        self.assertIn("PEN_HIGH_MONTHLY_INTEREST", ids("Interest at 3% per month on delayed rent.", "PENALTY"))
        self.assertIn("DEP_LARGE", ids("The security deposit shall be six months' rent.", "DEPOSIT"))
        self.assertIn("TERM_SHORT_NOTICE", ids("The Landlord may terminate by giving seven days' notice.", "TERMINATION"))

    def test_thresholds(self):
        self.assertNotIn("PEN_HIGH_MONTHLY_INTEREST", ids("Interest at 1% per month on delayed rent.", "PENALTY"))
        self.assertNotIn("REN_RENT_INCREASE_HIGH", ids("On renewal rent shall be increased by 5%.", "RENEWAL"))
        self.assertIn("REN_RENT_INCREASE_HIGH", ids("On renewal rent shall be increased by 15%.", "RENEWAL"))
        self.assertNotIn("DEP_LARGE", ids("The security deposit shall be two months' rent.", "DEPOSIT"))
        self.assertNotIn("TERM_SHORT_NOTICE", ids("The Landlord may terminate by giving thirty days' notice.", "TERMINATION"))

    def test_unless_suppresses(self):
        self.assertNotIn("TERM_LOCKIN", ids("A lock-in of six months shall apply to both parties.", "TERMINATION"))
        self.assertNotIn("ENTRY_ANYTIME", ids("In an emergency the Landlord may enter without notice.", "ENTRY"))
        self.assertNotIn("DEP_NO_TIMELINE", ids("The deposit shall be refunded within 15 days of vacating.", "DEPOSIT"))

    def test_favourable(self):
        self.assertIn("MAINT_WEAR_TEAR_EXCEPTED", ids("Keep the premises in good condition, normal wear and tear excepted.", "MAINTENANCE"))
        self.assertIn("TERM_MUTUAL", ids("Either party may terminate with one month's notice.", "TERMINATION"))


class TestDocChecks(unittest.TestCase):
    def test_parsers(self):
        self.assertEqual(parse_amounts("Rs. 2,50,000/- and ₹25,000"), [250000.0, 25000.0])
        self.assertEqual(sorted(parse_durations_days("fifteen (15) days and three months")), [15, 90])

    def test_notice_asymmetry_and_ratio(self):
        clauses = [
            {"index": 1, "clause_type": "RENT", "text": "Monthly rent is Rs. 20,000 per month."},
            {"index": 2, "clause_type": "DEPOSIT", "text": "Security deposit of Rs. 1,20,000."},
            {"index": 3, "clause_type": "TERMINATION", "text": "The Landlord may terminate with 15 days notice. The Tenant must give three months notice."},
        ]
        found = {f.check_id: f for f in run_document_checks(clauses)}
        self.assertIn("DOC_NOTICE_ASYMMETRY", found)
        self.assertIn("DOC_DEPOSIT_RATIO", found)
        self.assertIn("6.0", found["DOC_DEPOSIT_RATIO"].title)
        self.assertIn("DOC_MISSING_MAINTENANCE", found)


class TestPipeline(unittest.TestCase):
    def test_risky_vs_balanced(self):
        a = Analyzer(engine="rules")
        risky = a.analyze_file(SAMPLES / "leave_and_license_risky.txt")
        fair = a.analyze_file(SAMPLES / "residential_lease_balanced.txt")
        self.assertEqual(risky["summary"]["rating"], "High")
        self.assertGreaterEqual(risky["summary"]["risk_counts"]["RISKY"], 14)
        self.assertEqual(fair["summary"]["rating"], "Low")
        self.assertEqual(fair["summary"]["risk_counts"]["RISKY"], 0)
        for c in risky["clauses"]:
            if c["risk"] == "RISKY":
                self.assertTrue(c["explanation"])

    def test_pdf_and_docx_match_txt(self):
        a = Analyzer(engine="rules")
        txt = a.analyze_file(SAMPLES / "leave_and_license_risky.txt")["summary"]
        pdf = a.analyze_file(SAMPLES / "leave_and_license_risky.pdf")["summary"]
        self.assertEqual(txt["risk_counts"], pdf["risk_counts"])
        docx_r = a.analyze_file(SAMPLES / "residential_lease_balanced.docx")["summary"]
        self.assertEqual(docx_r["risk_counts"]["RISKY"], 0)

    def test_html_report_escapes(self):
        from rental_risk.report import to_html
        rep = Analyzer(engine="rules").analyze_text("1. Rent <script>x</script> is Rs. 10,000 per month payable monthly.\n2. The Landlord may enter at any time.\n3. Deposit is refundable on vacating the flat.")
        html = to_html(rep)
        self.assertNotIn("<script>x", html)
        self.assertIn("&lt;script&gt;", html)


class TestModel(unittest.TestCase):
    def test_train_save_load_predict(self):
        rows = load_dataset()
        m = ClauseModel.train(rows)
        with tempfile.TemporaryDirectory() as d:
            p = m.save(Path(d) / "m.joblib")
            m2 = ClauseModel.load(p)
        pred = m2.predict("The Landlord may terminate at any time without any notice.")
        self.assertIn(pred["risk"], {"RISKY", "NEUTRAL", "TENANT_FAVORABLE"})
        self.assertAlmostEqual(sum(pred["risk_probs"].values()), 1.0, places=5)


if __name__ == "__main__":
    unittest.main()


class TestMoreData(unittest.TestCase):
    def test_prepare_then_load_and_train(self):
        import csv
        from rental_risk.prepare import prepare
        with tempfile.TemporaryDirectory() as d:
            sheet = Path(d) / "sheet.csv"
            n = prepare([SAMPLES / "leave_and_license_risky.txt"], sheet)
            self.assertGreaterEqual(n, 18)
            with open(sheet, encoding="utf-8-sig") as f:
                rows = list(csv.DictReader(f))
            rows[0]["risk"] = "favourable"          # alias is accepted
            rows[1]["risk"] = ""                    # unlabelled row is skipped
            rows[2]["clause_type"] = "NOT_A_TYPE"   # invalid row is skipped
            with open(sheet, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
            extra = load_dataset(sheet)
            self.assertEqual(len(extra), n - 2)
            self.assertEqual(extra[0]["risk"], "TENANT_FAVORABLE")
            both = load_dataset([ROOT / "data" / "clauses.csv", sheet])
            self.assertEqual(len(both), len(load_dataset()) + len(extra))
            ClauseModel.train(both)


class TestLongBlocks(unittest.TestCase):
    def test_split_long_keeps_every_sentence_once(self):
        from rental_risk.ingest import split_long
        s = ["The FIRST PARTY acknowledges the receipt of Rs. 17,000 paid by Mr. A. Kumar in cash on signing.",
             "This amount shall be treated as house deposit and first month's rent for the premises.",
             "The deposit shall be returned to the SECOND PARTY on vacation of the premises after deductions.",
             "It carries no interest."]
        text = " ".join(s * 2)
        parts = split_long(text)
        self.assertGreater(len(parts), 2)
        self.assertEqual(" ".join(parts), text)                 # nothing lost or duplicated
        self.assertTrue(all("Mr." not in p[-4:] for p in parts))  # never splits after an abbreviation

    def test_xlsx_round_trip(self):
        from rental_risk.prepare import prepare
        with tempfile.TemporaryDirectory() as d:
            book = Path(d) / "label.xlsx"
            n = prepare([SAMPLES / "clause_list.txt"], book)
            rows = load_dataset(book)
            self.assertEqual(len(rows), n)
