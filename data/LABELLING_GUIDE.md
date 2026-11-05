# Labelling guide

Each row is one clause. Fill in two columns; leave both blank to exclude a row.

## clause_type (pick one)
| Label | Use for |
|---|---|
| RENT | rent amount, due date, payment method, utilities, taxes, advance rent |
| DEPOSIT | security deposit amount, refund, deductions |
| TERMINATION | ending the agreement, notice to vacate, lock-in, eviction |
| RENEWAL | term length, renewal, extension, rent increase on renewal |
| MAINTENANCE | repairs, upkeep, painting, wear and tear, fixtures |
| PENALTY | late fees, interest on delay, fines, overstay charges |
| ENTRY | landlord visits, inspections, keys, access |
| LIABILITY | indemnity, who is responsible for loss, damage or injury, legal costs |
| USE | residential use, subletting, guests, pets, house rules |
| OTHER | parties, date, stamp duty, disputes, notices, amendments, anything else |

## risk (from the TENANT's point of view)
| Label | Meaning | Example |
|---|---|---|
| RISKY | Shifts cost, liability or control onto the tenant beyond what is usual, is one-sided, or vague in a way that can hurt the tenant | "The Owner may terminate at any time without notice." |
| NEUTRAL | Standard, balanced, or purely factual | "Rent is Rs. 20,000 per month, due by the 5th." |
| TENANT_FAVORABLE | Adds protection for the tenant beyond the usual | "Deposit refunded within 15 days, with itemised deductions." |

Also accepted: `favourable`, `favorable`, `tenant-favourable` (all become TENANT_FAVORABLE).

## Rules of thumb
- Judge the clause as written, not what you guess the landlord intends.
- A clause with one risky part is RISKY even if the rest is fine.
- If the clause is unclear and the unclear part could cost the tenant, it is RISKY.
- Two people should label the same 50–100 clauses independently; compare to report agreement (Cohen's kappa).
- Keep a separate set of agreements aside for testing and never train on it.
