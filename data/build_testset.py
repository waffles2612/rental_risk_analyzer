"""Held-out test set. Written BEFORE the rules were tuned on data/clauses.csv and never used for tuning.

Keep it that way: tune rules and train models on clauses.csv only, and report final numbers here.
Run: python data/build_testset.py -> data/clauses_test.csv
"""
import csv
from pathlib import Path

R, N, F = "RISKY", "NEUTRAL", "TENANT_FAVORABLE"

ROWS = [
 # RENT
 ("RENT", "The Licensee shall pay a monthly compensation of Rs. 21,000 on or before the 3rd of each month through UPI.", N),
 ("RENT", "The Landlord may at any point demand an increased rent, which the Tenant shall be bound to pay from the following month.", R),
 ("RENT", "Payment of rent shall be made in cash and no written acknowledgement shall be required.", R),
 ("RENT", "The rent agreed herein shall not be increased during the period of this agreement.", F),
 ("RENT", "Municipal property tax for the premises shall be the liability of the Tenant.", R),
 ("RENT", "The Tenant shall pay the electricity bills directly to BESCOM as per the meter.", N),
 # DEPOSIT
 ("DEPOSIT", "A refundable deposit of Rs. 45,000 has been paid by the Tenant, receipt of which the Landlord hereby acknowledges.", N),
 ("DEPOSIT", "The Lessor shall return the deposit within ten days from the date the Lessee vacates, after deducting proven unpaid dues.", F),
 ("DEPOSIT", "The deposit will be refunded whenever the Owner is in a position to do so after the Tenant leaves.", R),
 ("DEPOSIT", "Painting charges equal to one month's rent will be adjusted from the deposit on vacating.", R),
 ("DEPOSIT", "The Tenant shall deposit an amount equivalent to six months' rent as security.", R),
 ("DEPOSIT", "The Owner shall provide a written list of deductions, with receipts, before adjusting any amount from the deposit.", F),
 ("DEPOSIT", "Should the Tenant leave before eleven months, the full deposit shall stand forfeited to the Owner.", R),
 # TERMINATION
 ("TERMINATION", "Either side can end this agreement with a written notice of thirty days.", F),
 ("TERMINATION", "The Owner may ask the Tenant to vacate with a notice of ten days.", R),
 ("TERMINATION", "The Licensee cannot cancel this agreement during its subsistence under any circumstances.", R),
 ("TERMINATION", "Should the Tenant exit before the lock-in of nine months ends, he shall be liable to pay rent for the unexpired lock-in period.", R),
 ("TERMINATION", "On expiry or earlier termination, the Licensee shall hand back the keys and the premises in good order.", N),
 ("TERMINATION", "The Lessor may cancel the lease on any breach of its terms without giving the Lessee any opportunity to rectify.", R),
 ("TERMINATION", "The Tenant may terminate without penalty if the premises become uninhabitable due to the Landlord's failure to repair.", F),
 # RENEWAL
 ("RENEWAL", "This agreement will be auto-renewed for successive eleven-month periods unless cancelled by the Tenant in writing three months in advance.", R),
 ("RENEWAL", "The Licensee shall be entitled to renew this licence for one more term on the same terms and conditions.", F),
 ("RENEWAL", "The rent for any renewed term shall be increased by twenty five percent.", R),
 ("RENEWAL", "The period of this licence is eleven months beginning 1 July 2026.", N),
 ("RENEWAL", "Any extension of this agreement shall be on terms mutually agreed and recorded in writing.", N),
 ("RENEWAL", "The rent on extension shall be decided by the Owner at the time of extension.", R),
 # MAINTENANCE
 ("MAINTENANCE", "Day-to-day minor repairs shall be the Tenant's responsibility; structural repairs shall be done by the Landlord.", F),
 ("MAINTENANCE", "Any repair of whatever nature required in the flat shall be carried out by the Tenant at his expense.", R),
 ("MAINTENANCE", "The Licensee shall hand back the premises freshly painted at his own cost.", R),
 ("MAINTENANCE", "The Tenant shall take reasonable care of the fixtures and fittings.", N),
 ("MAINTENANCE", "Leakages in the roof or walls shall be repaired by the Tenant at his cost.", R),
 ("MAINTENANCE", "The Owner shall be responsible for repairing any defect in the electrical wiring or plumbing within a week of complaint.", F),
 # PENALTY
 ("PENALTY", "In case of delay in payment, interest at 4% per month shall be charged on the amount due.", R),
 ("PENALTY", "A one-time late payment fee of Rs. 300 shall apply if rent is paid after the 10th.", N),
 ("PENALTY", "For each day the rent remains unpaid, a fine of Rs. 750 shall be levied.", R),
 ("PENALTY", "If the Tenant continues to occupy after expiry, he shall pay twice the monthly rent as damages.", R),
 ("PENALTY", "No penalty shall be levied if rent is paid within seven days of the due date.", F),
 # ENTRY
 ("ENTRY", "The Landlord may enter the flat for inspection with at least one day's prior notice to the Tenant.", F),
 ("ENTRY", "The Owner shall have unrestricted access to the premises at all times.", R),
 ("ENTRY", "The Owner retains a duplicate key and may open the flat in the Tenant's absence for inspection.", R),
 ("ENTRY", "In case of an emergency the Landlord may enter the premises without prior notice.", N),
 ("ENTRY", "The Licensor's representatives may visit the premises without any prior intimation.", R),
 # LIABILITY
 ("LIABILITY", "The Tenant shall indemnify the Owner against any and all claims whatsoever arising from the use of the premises.", R),
 ("LIABILITY", "Neither party shall be liable for losses not caused by its own negligence or breach.", F),
 ("LIABILITY", "The Owner shall in no event be liable for any loss or injury to the Tenant, his family or visitors.", R),
 ("LIABILITY", "The Tenant is advised to insure his personal belongings.", N),
 ("LIABILITY", "The Tenant shall bear the Owner's legal expenses in connection with any dispute under this agreement.", R),
 # USE
 ("USE", "The flat shall be used solely for residential purposes.", N),
 ("USE", "Overnight visitors are prohibited without the Landlord's consent.", R),
 ("USE", "The Tenant shall not sublet the premises.", N),
 ("USE", "The Tenant may keep pets with the Landlord's consent, which shall not be unreasonably withheld.", F),
 ("USE", "Friends and relatives of the Licensee are not permitted to visit the premises.", R),
 ("USE", "The Tenant shall abide by the bye-laws of the apartment association.", N),
 # OTHER
 ("OTHER", "This agreement is entered into at Pune on 12 May 2026.", N),
 ("OTHER", "The Landlord may unilaterally alter any condition of this agreement and such alteration shall bind the Tenant.", R),
 ("OTHER", "All disputes shall be decided by an arbitrator nominated by the Owner alone.", R),
 ("OTHER", "Any modification to this agreement must be in writing and signed by both parties.", F),
 ("OTHER", "The Tenant waives his right to approach the Rent Authority for any grievance under this agreement.", R),
 ("OTHER", "The stamp duty on this agreement shall be borne by the Tenant and the Landlord in equal shares.", N),
 ("OTHER", "This agreement contains the entire understanding between the parties.", N),
]


def main():
    out = Path(__file__).with_name("clauses_test.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "text", "clause_type", "risk", "source"])
        w.writeheader()
        for i, (t, text, risk) in enumerate(ROWS, 1):
            w.writerow({"id": f"t{i:03d}", "text": text, "clause_type": t, "risk": risk, "source": "authored-heldout"})
    print(f"{len(ROWS)} held-out clauses -> {out}")


if __name__ == "__main__":
    main()
