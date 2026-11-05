"""Seed dataset: hand-written clauses labelled by clause type and tenant risk.

Labels: clause_type in RENT, DEPOSIT, TERMINATION, RENEWAL, MAINTENANCE, PENALTY, ENTRY, LIABILITY, USE, OTHER
        risk in RISKY, NEUTRAL, TENANT_FAVORABLE (from the tenant's point of view)

These were written to mirror wording found in Indian leave-and-licence and lease agreements, including
paraphrases the keyword rules do NOT cover, so the rule baseline is genuinely tested. Replace / extend with
clauses from real agreements annotated by your team (deck step 02) before reporting final numbers.
Run: python data/build_dataset.py  -> data/clauses.csv
"""
import csv
from pathlib import Path

R, N, F = "RISKY", "NEUTRAL", "TENANT_FAVORABLE"

DATA = {
"RENT": [
 ("The monthly rent of Rs. 18,000 shall be paid on or before the 7th day of each English calendar month by NEFT to the Landlord's account.", N),
 ("The Tenant shall pay rent of Rs. 22,500 per month in advance on or before the 5th of every month.", N),
 ("The Lessee shall pay the rent in cash only and the Lessor shall not be obliged to issue any receipt for the same.", R),
 ("The Landlord reserves the right to revise the rent from time to time as he may deem fit and the Tenant shall pay the revised rent.", R),
 ("The Owner may increase the rent whenever the market rate in the locality goes up, and the new rent shall be binding on the Tenant.", R),
 ("The Licensor shall acknowledge every payment of the licence fee by issuing a signed receipt or an email confirmation.", F),
 ("The rent shall remain fixed for the entire term of this agreement and shall not be revised during the term.", F),
 ("Society maintenance charges shall be paid by the Owner, and electricity charges as per actual consumption shall be paid by the Tenant.", N),
 ("All present and future taxes, cesses and levies on the said premises, including property tax, shall be paid by the Tenant.", R),
 ("Twelve months' rent shall be paid in advance at the time of signing this agreement and shall not be adjusted against any dues.", R),
 ("The licence fee shall be Rs. 15,000 per month inclusive of society maintenance charges.", N),
 ("Rent shall be enhanced by 5% every year on the anniversary of the commencement date.", N),
 ("Any increase in the rent shall be by mutual written agreement of both parties and shall not exceed 5% per year.", F),
 ("Water charges, if any, shall be shared equally by all the occupants of the building.", N),
 ("The Tenant shall additionally bear any charges that the Landlord may levy from time to time for common facilities, without limit.", R),
 ("Rent paid by the Tenant shall be acknowledged in a rent register maintained by both parties and signed by the Landlord.", F),
],
"DEPOSIT": [
 ("The Tenant has paid an interest-free refundable security deposit of Rs. 50,000, which shall be returned at the time of vacating after adjusting dues, if any.", F),
 ("The security deposit of Rs. 40,000 shall be refunded within 30 days of the Tenant handing over vacant and peaceful possession of the premises.", F),
 ("The deposit shall be returned to the Lessee only after the Lessor finds a new tenant for the premises.", R),
 ("The Licensor may deduct from the deposit such amounts as he considers appropriate towards damages, and his decision shall be final.", R),
 ("At the time of vacating, two months' rent shall be deducted from the deposit towards repainting of the flat.", R),
 ("Any deduction from the deposit shall be supported by bills and an itemised statement shared with the Tenant.", F),
 ("The security deposit shall be equivalent to ten months' rent.", R),
 ("The security deposit shall not exceed two months' rent.", F),
 ("An amount of Rs. 10,000 out of the deposit is a one-time non-refundable brokerage and documentation charge.", R),
 ("If the deposit is not refunded on the due date, the Landlord shall pay interest at 12% per annum on the delayed amount.", F),
 ("The deposit shall be refunded subject to deduction of unpaid rent, unpaid utility bills and the cost of repairing damage beyond normal wear and tear.", N),
 ("The Tenant shall not be entitled to adjust the security deposit against the rent for the last month.", N),
 ("Upon handing over of keys, the deposit will be returned, less any deductions the Owner deems necessary.", R),
 ("Both parties shall jointly inspect the premises before refund and record any damage in writing.", F),
 ("The Owner shall refund the deposit by bank transfer simultaneously with the Tenant handing over the keys.", F),
 ("In case the Lessee vacates before the end of the term, the Lessor shall be entitled to retain the entire security deposit.", R),
],
"TERMINATION": [
 ("Either party may terminate this agreement by giving the other party one month's prior written notice.", F),
 ("The Landlord may terminate this tenancy by giving the Tenant seven days' notice.", R),
 ("The Licensor may revoke this licence whenever he requires the premises for his own use, without any notice.", R),
 ("The Tenant shall not be allowed to terminate this agreement before the expiry of the term.", R),
 ("The lock-in period shall be six months, during which neither party may terminate except for breach.", N),
 ("If the Tenant leaves during the first year, he shall pay the rent for the balance period of the agreement.", R),
 ("The Tenant may terminate this agreement by giving two months' notice; the Landlord may terminate by giving one month's notice.", R),
 ("The Landlord may terminate the agreement only if the Tenant defaults in paying rent for two consecutive months, after giving thirty days' written notice to remedy the default.", F),
 ("On termination, the Tenant shall hand over vacant and peaceful possession of the premises in the same condition, subject to normal wear and tear.", F),
 ("The Tenant may end the tenancy early without penalty on account of job transfer by giving one month's notice.", F),
 ("If the Tenant fails to vacate on expiry, the Landlord shall be free to remove the Tenant's belongings and take possession of the premises.", R),
 ("Upon any breach by the Lessee, the Lessor may immediately cancel this lease and the Lessee shall vacate forthwith.", R),
 ("The notice period for termination by either party shall be sixty days.", F),
 ("This agreement shall come to an end on the expiry of the term unless renewed in writing.", N),
 ("The Licensee shall vacate the premises within 48 hours if asked to do so by the Licensor.", R),
 ("Notice of termination shall be given in writing to the address mentioned above or by email.", N),
],
"RENEWAL": [
 ("This agreement may be renewed for a further period on mutually agreed terms by executing a fresh agreement.", N),
 ("Unless either party gives notice sixty days before expiry, this agreement shall stand extended for another eleven months on the same terms.", R),
 ("The Tenant shall have the first right to renew this tenancy for a further period of three years.", F),
 ("On renewal the rent shall be increased by 20% of the existing rent.", R),
 ("Renewal shall be at the discretion of the Landlord, who may fix any rent he considers fit for the renewed term.", R),
 ("The rent on renewal shall not be more than 5% higher than the last rent paid.", F),
 ("The licence is for eleven months from 1st June 2026 to 30th April 2027.", N),
 ("The tenancy shall automatically continue on a month-to-month basis after expiry, at a rent 10% higher, until terminated.", R),
 ("Any renewal shall require the written consent of both the Landlord and the Tenant.", N),
 ("This lease shall be for a period of 36 months with an escalation of 5% after every 12 months.", N),
 ("The Tenant may, at his option, extend the lease for two further terms of one year each at the same rent.", F),
 ("The agreement will be deemed renewed if the Tenant continues to stay after expiry, and the Tenant will then be bound by any revised terms the Owner sets.", R),
 ("The term of this agreement is eleven months commencing on the date of signing.", N),
 ("Fresh stamp duty and registration charges on renewal shall be borne equally by both parties.", N),
],
"MAINTENANCE": [
 ("Minor repairs such as replacement of bulbs, tube lights and tap washers shall be done by the Tenant at his cost.", N),
 ("All major repairs, including structural repairs, seepage and leakage, shall be carried out by the Landlord at his own cost.", F),
 ("The Tenant shall bear the cost of every repair to the premises, whether minor or major, during the tenancy.", R),
 ("The Lessee shall keep the premises in good and tenantable condition, reasonable wear and tear excepted.", F),
 ("The Licensee shall be responsible for any damage to the premises including that arising from normal use and ageing of the fittings.", R),
 ("Repairs to the overhead water tank, roof and main drainage lines shall be the responsibility of the Tenant.", R),
 ("The Tenant shall get the entire flat repainted at his own cost before vacating, regardless of its condition.", R),
 ("The Landlord shall attend to any repair request within seven days, failing which the Tenant may carry out the repair and deduct the cost from the rent.", F),
 ("The Tenant shall not make any structural alterations to the premises without the written consent of the Landlord.", N),
 ("The fittings and fixtures listed in Annexure A are provided in working condition.", N),
 ("Annual servicing of the air conditioners and the water purifier shall be done by the Tenant.", N),
 ("If any appliance supplied by the Owner breaks down, the Tenant shall replace it with a new one at his cost.", R),
 ("Pest control of the premises shall be arranged by the Landlord twice a year at his cost.", F),
 ("The Tenant shall inform the Landlord promptly of any defect requiring repair.", N),
 ("The Licensee shall pay for damage caused by natural calamities, fire or water leakage from adjoining flats.", R),
],
"PENALTY": [
 ("A late fee of Rs. 200 shall be charged if rent is paid after the 10th of the month.", N),
 ("Rent not paid by the due date shall attract interest at 18% per annum.", N),
 ("Delayed payment shall attract interest at the rate of 5% per month, compounded monthly.", R),
 ("A penalty of Rs. 1,000 for every day of delay in payment of rent shall be payable by the Tenant.", R),
 ("If the Tenant overstays beyond the term, he shall pay damages at three times the monthly rent for every month of overstay.", R),
 ("No late fee shall be charged for payments received within five days of the due date.", F),
 ("Any cheque that is dishonoured shall attract a charge of Rs. 500 in addition to bank charges.", N),
 ("Breach of any condition of this agreement, however small, shall result in a fine of Rs. 25,000.", R),
 ("Late payment charges shall not exceed 2% of the monthly rent in any month.", F),
 ("If rent is unpaid for fifteen days the Landlord may lock the premises until the dues are cleared.", R),
 ("The Tenant shall reimburse the Landlord for reasonable costs actually incurred because of a breach by the Tenant.", N),
 ("Failure to pay rent on time will result in the deposit being forfeited.", R),
],
"ENTRY": [
 ("The Landlord may inspect the premises once a month at a mutually convenient time after giving 24 hours' notice.", F),
 ("The Owner and his family members may visit the premises whenever they wish.", R),
 ("The Licensor shall have free access to the premises at all times for any purpose.", R),
 ("In an emergency such as fire or water leakage, the Landlord may enter the premises without notice.", N),
 ("The Landlord shall keep a spare key of the flat and may use it to enter when the Tenant is away.", R),
 ("During the last month of tenancy, the Tenant shall allow prospective tenants to view the premises at reasonable hours with prior intimation.", N),
 ("The Landlord shall not enter the premises without the Tenant's consent except in an emergency.", F),
 ("The Owner may carry out surprise inspections of the premises.", R),
 ("Inspection of the premises shall be carried out only in the presence of the Tenant or his authorised representative.", F),
 ("The Landlord may enter between 10 am and 6 pm on weekdays to carry out repairs after informing the Tenant.", N),
 ("The Lessor's agents may show the flat to buyers at any hour without informing the Lessee.", R),
],
"LIABILITY": [
 ("The Tenant shall indemnify and keep indemnified the Landlord against all claims, losses and costs of any kind whatsoever.", R),
 ("The Tenant shall be liable only for loss or damage caused by his own negligence or wilful default.", F),
 ("The Landlord shall not be responsible for any injury, loss or damage to the Tenant or his property for any reason.", R),
 ("The Landlord shall be liable for any injury caused by structural defects in the building of which he was informed.", F),
 ("The Tenant shall insure his own belongings; the building insurance shall be maintained by the Owner.", N),
 ("The Licensee alone shall be answerable for any accident occurring in the premises or common areas, irrespective of the cause.", R),
 ("Each party shall indemnify the other against losses arising from its own breach of this agreement.", F),
 ("The Owner will not be held responsible for theft of the Tenant's belongings from the premises.", N),
 ("The Tenant shall be responsible for any fines imposed by the society on account of the conduct of the Tenant or his guests.", N),
 ("The Tenant shall pay the Landlord's legal costs in any dispute, irrespective of who succeeds.", R),
 ("The Tenant shall be solely liable for all dues of the building society, including dues pending from before the start of the tenancy.", R),
],
"USE": [
 ("The premises shall be used only for residential purposes by the Tenant and his family.", N),
 ("The Tenant shall not sublet, assign or part with possession of the premises or any part thereof.", N),
 ("No guest shall stay in the premises for more than one night without the Owner's written approval.", R),
 ("The Tenant may have guests and visitors in accordance with the society bye-laws.", F),
 ("The Licensee shall not keep any pets in the premises.", N),
 ("The Tenant shall not cook non-vegetarian food in the premises.", R),
 ("The Tenant shall not carry on any illegal or immoral activity in the premises.", N),
 ("The Tenant may sublet a room with the Landlord's consent, which shall not be unreasonably refused.", F),
 ("The Tenant shall follow all rules of the housing society, as amended from time to time by the society.", N),
 ("The Lessee shall not have friends of the opposite gender visit the premises.", R),
 ("The Tenant may install a washing machine, internet connection and other household appliances at his own cost and remove them on vacating.", F),
 ("The Tenant shall not create any nuisance or disturbance to the neighbours.", N),
 ("The Licensee shall be home by 10 pm every night and the main gate will be locked after that.", R),
 ("The Tenant may work from home and receive deliveries at the premises.", F),
],
"OTHER": [
 ("This agreement is made at Chennai on this 3rd day of March 2026 between the parties named above.", N),
 ("This agreement is executed in duplicate and each party shall retain one original copy.", N),
 ("The stamp duty and registration charges for this agreement shall be shared equally by both parties.", N),
 ("The Tenant shall bear the entire stamp duty, registration charges and the Landlord's legal fees for this agreement.", R),
 ("Any dispute shall be referred to an arbitrator appointed solely by the Landlord, whose decision shall be final and binding.", R),
 ("Any dispute between the parties shall be settled by the Rent Authority having jurisdiction over the premises.", N),
 ("The Owner may change the terms of this agreement by giving notice to the Tenant, and the Tenant shall be bound by the changes.", R),
 ("No amendment to this agreement shall be valid unless made in writing and signed by both parties.", F),
 ("The Tenant agrees not to approach any court or authority in respect of any matter arising out of this agreement.", R),
 ("Annexure A lists the furniture and fixtures provided with the premises.", N),
 ("Notices under this agreement shall be sent by registered post or email to the addresses given above.", N),
 ("The Tenant shall furnish a copy of his identity proof and police verification form as required by law.", N),
 ("The Tenant has read and understood all terms and has signed this agreement voluntarily.", N),
 ("The Landlord confirms that he has clear title to the premises and the right to let it out.", F),
],
}


def main():
    out = Path(__file__).with_name("clauses.csv")
    rows, i = [], 0
    for ctype, items in DATA.items():
        for text, risk in items:
            i += 1
            rows.append({"id": f"c{i:03d}", "text": text, "clause_type": ctype, "risk": risk, "source": "authored-seed"})
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "text", "clause_type", "risk", "source"])
        w.writeheader()
        w.writerows(rows)
    from collections import Counter
    print(f"{len(rows)} clauses -> {out}")
    print("types:", dict(Counter(r["clause_type"] for r in rows)))
    print("risk :", dict(Counter(r["risk"] for r in rows)))


if __name__ == "__main__":
    main()
