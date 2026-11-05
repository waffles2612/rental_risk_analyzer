# Authoring helper: writes rental_risk/rules.json (the JSON is the source of truth).
import json, sys

T = "{T}"; L = "{L}"; S = "{S}"

clause_types = {
    "RENT": {"label": "Rent & payment", "keywords": [
        [r"\bmonthly (?:rent|licen[cs]e fee)\b", 3], [r"\brent\b|\blicen[cs]e fee\b", 1], [r"\bpayable\b", 1], [r"\bper month\b", 1],
        [r"\bdue (?:on|by|before)\b", 2], [r"\bescalat", 2], [r"\bbank transfer\b|\bcheque\b|\bupi\b|\bneft\b", 2],
        [r"\bproperty tax\b|\bmaintenance charges\b|\butility bills?\b|\belectricity (?:and|&) water\b", 2],
        [r"\breceipt\b", 1]]},
    "DEPOSIT": {"label": "Security deposit", "keywords": [
        [r"\bsecurity deposit\b", 4], [r"\bdeposit\b", 2], [r"\brefund", 2], [r"\binterest[- ]free\b", 2],
        [r"\badvance amount\b", 2], [r"\bdeduct", 1]]},
    "TERMINATION": {"label": "Termination & notice", "keywords": [
        [r"\bterminat", 3], [r"\bvacate\b|\bvacating\b", 2], [r"\bnotice period\b", 2], [r"\block[- ]?in\b", 3],
        [r"\bevict", 3], [r"\bquit\b", 1], [r"\bend (?:this|the) (?:agreement|tenancy)\b", 2], [r"\bnotice\b", 1]]},
    "RENEWAL": {"label": "Renewal & term", "keywords": [
        [r"\brenew", 4], [r"\bextend|\bextension\b", 2], [r"\bfurther period\b", 2], [r"\bexpir", 2],
        [r"\bperiod of (?:eleven|11|twelve|12) months\b", 2], [r"\bterm of\b", 1]]},
    "MAINTENANCE": {"label": "Repairs & maintenance", "keywords": [
        [r"\brepair", 3], [r"\bmaintenance\b", 2], [r"\bmaintain", 2], [r"\bwear and tear\b", 3],
        [r"\bpainting\b|\bwhitewash", 2], [r"\bplumbing\b|\belectrical\b|\bfixtures\b|\bfittings\b|\bappliances\b", 2],
        [r"\bpest\b|\bleak", 2], [r"\bdamage", 1], [r"\bgood (?:and tenantable )?condition\b", 2]]},
    "PENALTY": {"label": "Penalties & late fees", "keywords": [
        [r"\blate (?:fee|payment|charge)", 4], [r"\bpenalt", 4], [r"\bfine\b", 3], [r"\binterest (?:at|of)\b", 2],
        [r"\bliquidated damages\b", 3], [r"\bper day\b|\beach day\b", 2], [r"\bdelay", 1], [r"\bdouble\b|\btwice\b", 1], [r"\bdefault", 2], [r"\bbreach", 1]]},
    "ENTRY": {"label": "Landlord entry & access", "keywords": [
        [r"\benter\b|\bentry\b", 3], [r"\binspect", 3], [r"\baccess\b", 2], [r"\bduplicate key|\bspare key", 3],
        [r"\bvisit\b", 1], [r"\bprospective (?:tenants|buyers)\b", 2]]},
    "LIABILITY": {"label": "Liability & indemnity", "keywords": [
        [r"\bindemnif", 4], [r"\bliab", 3], [r"\bresponsible for any (?:loss|damage|injury)", 2],
        [r"\bloss or damage\b", 2], [r"\binsur", 2], [r"\bclaims?\b", 1], [r"\btheft\b|\binjur", 2]]},
    "USE": {"label": "Use of premises", "keywords": [
        [r"\bsub-?let", 4], [r"\bassign", 2], [r"\bpets?\b", 3], [r"\bguests?\b|\bvisitors?\b", 3],
        [r"\bresidential purpose", 3], [r"\bcommercial\b", 1], [r"\balteration|\bstructural changes\b", 2],
        [r"\bsmok", 2], [r"\boccup", 1], [r"\bnuisance\b|\bnoise\b", 2], [r"\bfamily\b", 1]]},
}

R = []
def rule(id, types, pattern, risk, severity, title, explanation, ask="", unless=None, value_min=None, value_max=None):
    r = {"id": id, "types": types, "pattern": pattern, "risk": risk, "severity": severity,
         "title": title, "explanation": explanation}
    if ask: r["ask"] = ask
    if unless: r["unless"] = unless
    if value_min is not None: r["value_min"] = value_min
    if value_max is not None: r["value_max"] = value_max
    R.append(r)

RISKY, FAV = "RISKY", "TENANT_FAVORABLE"

# ---------- Generic (any clause type) ----------
rule("GEN_SOLE_DISCRETION", ["*"], r"\b(?:sole|absolute|exclusive|own)(?: and (?:absolute|exclusive))? discretion\b",
     RISKY, "high", "Decided at the landlord's sole discretion",
     "This clause lets one side decide on its own, with no objective standard and no way for you to challenge the decision.",
     "Replace 'sole discretion' with an objective test (e.g. 'reasonable, documented costs') or require mutual agreement.")
rule("GEN_WAIVER", ["*"], r"\b(?:waive[sd]?|waiver of|give[sn]? up|relinquish(?:es)?)\b" + S + r"\b(?:rights?|claims?|remed(?:y|ies)|objections?)\b",
     RISKY, "high", "You give up legal rights",
     "The clause asks you to waive rights or remedies you would otherwise have. Waivers like this are hard to undo once signed.",
     "Strike the waiver, or limit it to a specific, named situation.")
rule("GEN_UNILATERAL_AMEND", ["*"], r"\b(?:modify|amend|change|alter|revise)\b" + S + r"\b(?:terms|rules|conditions|agreement|regulations)\b" + S + r"(?:at any time|unilaterally|without (?:the )?(?:tenant'?s? |lessee'?s? |licensee'?s? )?(?:consent|notice|approval))",
     RISKY, "high", "Terms can be changed one-sidedly",
     "One party can change the agreement after you sign it, so the deal you agreed to may not be the deal you get.",
     "Add: 'No change to this agreement is valid unless made in writing and signed by both parties.'")
rule("GEN_OPEN_ENDED", ["*"], r"\b(?:whatsoever|howsoever|irrespective of (?:the )?(?:cause|reason|circumstances?|fault))\b",
     RISKY, "medium", "Open-ended scope",
     "Words like 'whatsoever' or 'irrespective of the cause' make the obligation unlimited, including situations that are not your fault.",
     "Limit the obligation to losses caused by your own negligence or breach.")
rule("GEN_NO_LEGAL_RECOURSE", ["*"], r"\b(?:shall not|cannot|will not|may not)\b" + S + r"\b(?:approach|move|file|go to|initiate)\b" + S + r"\b(?:court|tribunal|authority|legal proceedings?|rent controller)\b",
     RISKY, "high", "Blocks you from legal remedies",
     "The clause tries to stop you from going to a court or rent authority. You should never sign away access to dispute resolution.",
     "Delete this clause; any dispute clause should apply equally to both parties.")

# ---------- Deposit ----------
rule("DEP_NONREFUNDABLE", ["DEPOSIT", "RENT"], r"\bnon[- ]?refundable\b",
     RISKY, "high", "Non-refundable money",
     "Part of what you pay will not come back to you, even if you leave the property in perfect condition.",
     "Ask for the full deposit to be refundable, minus documented damage beyond normal wear and tear.")
rule("DEP_FORFEIT", ["DEPOSIT", "TERMINATION", "PENALTY"], r"\bforfeit",
     RISKY, "high", "Deposit can be forfeited",
     "The landlord can keep the whole deposit as a penalty, not just the cost of actual damage or unpaid rent.",
     "Limit deductions to unpaid rent and documented repair costs; remove forfeiture.")
rule("DEP_FIXED_DEDUCTION", ["DEPOSIT", "MAINTENANCE"], r"\bdeduct\w*" + S + r"\b(?:painting|repainting|whitewash\w*|cleaning|deep clean\w*)\b|\b(?:painting|repainting|whitewash\w*|cleaning)\b" + S + r"\bdeduct",
     RISKY, "medium", "Automatic deductions from deposit",
     "A fixed charge (often painting or cleaning) comes out of your deposit whatever condition you leave the home in. Repainting after normal use is usually ordinary wear and tear.",
     "Make painting/cleaning deductions conditional on actual damage, with receipts.")
rule("DEP_NO_TIMELINE", ["DEPOSIT"], r"\b(?:refunded|returned|repaid|repay|give back|refund (?:of|the)|(?:shall|will) (?:be )?refund)\b",
     RISKY, "medium", "No deadline for returning the deposit",
     "The clause says the deposit will be returned but gives no deadline, so the landlord can delay it indefinitely.",
     "Add a fixed timeline, e.g. 'refunded within 15 days of handing over possession'.",
     unless=r"\bwithin\s+(?:\w+\s*)?(?:\(\d+\)\s*)?(?:days?|weeks?|working days)\b|\bat the time of (?:handing over|vacating|handover)|\bon the (?:day|date) of (?:vacating|handing over|handover)|\bsimultaneously\b|\bimmediately\b|\bsame day\b")
rule("DEP_TIMELINE", ["DEPOSIT"], r"\b(?:refund\w*|return\w*|repaid)\b" + S + r"(?:\bwithin\s+(?:\w+\s*)?(?:\(\d+\)\s*)?(?:days?|weeks?|working days)\b|\bat the time of (?:handing over|vacating)|\bsimultaneously\b|\bimmediately\b)",
     FAV, "low", "Clear refund deadline",
     "The deposit has a defined return deadline, which protects you from indefinite delays.")
rule("DEP_ITEMISED", ["DEPOSIT"], r"\bitemi[sz]ed\b|\b(?:supported|accompanied) by (?:bills|receipts|invoices)\b|\bwritten statement of (?:deductions|account)\b|\bwith (?:supporting )?(?:bills|receipts|invoices)\b",
     FAV, "low", "Deductions must be justified",
     "Any deduction must be backed by an itemised statement or receipts, so you can check what you are charged for.")

# ---------- Termination ----------
rule("TERM_LANDLORD_ANYTIME", ["TERMINATION"], r"\b(?:at any time|for any reason|without (?:assigning|giving|stating|any) (?:any )?reasons?|without (?:any )?(?:prior )?notice)\b",
     RISKY, "high", "Can be ended without reason or notice",
     "The tenancy can be ended at any time or without a reason, leaving you exposed to sudden loss of your home.",
     "Require a written notice period (at least 1 month) and limit landlord termination to specific breaches.",
     unless=r"\b(?:either party|both parties|either of the parties)\b")
rule("TERM_LOCKIN", ["TERMINATION", "RENEWAL"], r"\block[- ]?in\b",
     RISKY, "medium", "Lock-in period",
     "You cannot leave during the lock-in without a penalty. If your plans change (job, studies, family), you may still owe money.",
     "Keep the lock-in short and make it apply to both sides equally.",
     unless=r"\b(?:either party|both parties|mutual|binding on both)\b")
rule("TERM_PAY_REMAINDER", ["TERMINATION", "PENALTY"], r"\b(?:{R}|pay|liable)\b" + S + r"\b(?:remaining|balance|unexpired|entire|whole|rest of the)\b" + S + r"\b(?:period|term|months|lock[- ]?in|tenure)\b",
     RISKY, "high", "Pay rent for months you don't live there",
     "If you leave early you must pay rent for the rest of the term, which can be a large lump sum.",
     "Cap early-exit cost at one month's rent, or allow you to leave once a replacement tenant is found.")
rule("TERM_ONLY_LANDLORD", ["TERMINATION"], r"\bonly (?:the )?" + L + r"\b" + S + r"\bterminat|\b" + T + r"\s+(?:shall|will) not (?:be entitled|have (?:the|any) right|be permitted)" + S + r"\bterminat",
     RISKY, "high", "Only the landlord can end the agreement",
     "The right to terminate is one-sided. You are bound for the full term while the landlord is not.",
     "Make termination rights and notice periods equal for both parties.")
rule("TERM_SELF_HELP", ["TERMINATION", "PENALTY", "ENTRY", "*"], r"\b(?:disconnect|cut off|stop|suspend)\w*" + S + r"\b(?:electricity|water|power|gas|supply|supplies)\b|\bchange the locks?\b|\bremove (?:the )?(?:" + T + r"'?s? )?(?:belongings|possessions|articles)\b|\bforcibly\b|\btake (?:back )?possession\b" + S + r"\bwithout\b",
     RISKY, "high", "Self-help eviction",
     "The landlord may cut utilities, change locks or remove your belongings. Evicting a tenant normally requires due legal process, not self-help.",
     "Delete this clause entirely.")
rule("TERM_MUTUAL", ["TERMINATION"], r"\b(?:either party|both parties|either of the parties)\b" + S + r"\b(?:terminat|notice|vacat)",
     FAV, "low", "Mutual termination rights",
     "Both sides can end the agreement on the same terms, so neither party has an unfair advantage.")

# ---------- Renewal ----------
rule("REN_AUTO", ["RENEWAL", "TERMINATION"], r"\bautomatic(?:ally)?\b" + S + r"\b(?:renew|extend|continu)|\b(?:renew|extend)\w*" + S + r"\bautomatic|\bdeemed (?:to (?:have been|be) )?(?:renewed|extended)\b|\bshall continue\b" + S + r"\bunless\b" + S + r"\bnotice\b",
     RISKY, "medium", "Automatic renewal",
     "The agreement renews by itself unless someone gives notice in time. Miss the window and you can be bound for another term, often at a higher rent.",
     "Put the notice deadline in your calendar, or ask for renewal only by mutual written agreement.")
rule("REN_RENT_INCREASE_HIGH", ["RENEWAL", "RENT"], r"\b(?:increase|enhance|escalat|hike|revis)\w*" + S + r"(\d+(?:\.\d+)?)\s*(?:%|percent|per cent)",
     RISKY, "high", "Steep rent increase",
     "The rent rises by 10% or more, which is above typical annual increases (often around 5-10%).",
     "Negotiate a lower cap (e.g. 5%) or a fixed rent for the first renewal.", value_min=10)
rule("REN_UNBOUNDED_INCREASE", ["RENEWAL", "RENT"], r"\b(?:increase|enhance|escalat|hike|revis)\w*" + S + r"\b(?:as (?:decided|determined|fixed) by|at the (?:sole )?discretion|prevailing market|as the " + L + r" (?:deems|thinks|considers) fit|mutually agreed at the time)\b|\b" + L + r"\s+(?:may|can|shall be entitled to)\s+(?:increase|revise|enhance)\b(?![^.]*(?:%|percent|per cent))",
     RISKY, "high", "Rent increase with no cap",
     "The rent can be raised without a fixed limit, so you cannot predict what renewal will cost.",
     "Ask for a fixed percentage cap written into the agreement.")
rule("REN_TENANT_OPTION", ["RENEWAL"], r"\b" + T + r"\s+(?:shall have|has|will have|is entitled to)\s+(?:the|an)\s+(?:option|right)\s+to\s+(?:renew|extend)",
     FAV, "low", "Renewal at your option",
     "You decide whether to renew, which gives you security of tenure.")
rule("REN_CAPPED", ["RENEWAL", "RENT"], r"\b(?:not (?:exceed|be more than|more than)|maximum of|capped at|at most)\s*(?:\w+\s*)?(?:\(\d+\)\s*)?\d*\s*(?:%|percent|per cent)",
     FAV, "low", "Rent increase is capped",
     "Any increase is limited to a stated maximum, so future rent is predictable.")

# ---------- Maintenance ----------
rule("MAINT_ALL_REPAIRS", ["MAINTENANCE"], r"\b" + T + r"\b" + S + r"\b(?:all|any|every)\b" + S + r"\b(?:repairs?|maintenance|replacement)\b|\ball (?:repairs|maintenance|replacements?)\b" + S + r"\b(?:borne|paid|responsibility|cost)\b" + S + r"\b" + T + r"\b",
     RISKY, "high", "You pay for all repairs",
     "Making you responsible for every repair includes major and structural problems that are normally the landlord's job.",
     "Split responsibilities: minor day-to-day repairs for you, major/structural repairs for the landlord.",
     unless=r"\b(?:minor|day[- ]to[- ]day|small)\b")
rule("MAINT_STRUCTURAL_TENANT", ["MAINTENANCE"], r"\b" + T + r"\b" + S + r"\b(?:repair|replace|bear|pay)\w*" + S + r"\b(?:structural|roof|foundation|walls?|pipelines?|wiring)\b|\b(?:structural|major)\b" + S + r"\b(?:borne|paid) by (?:the )?" + T + r"\b",
     RISKY, "high", "Structural repairs on you",
     "Structural repairs (roof, walls, main plumbing or wiring) are expensive and are normally the owner's responsibility.",
     "Make structural and major repairs the landlord's responsibility.")
rule("MAINT_WEAR_TEAR_INCLUDED", ["MAINTENANCE", "DEPOSIT"], r"\b(?:including|irrespective of|regardless of|even if due to)\b" + S + r"\b(?:normal|reasonable|fair|ordinary) wear and tear\b",
     RISKY, "high", "Charged for normal wear and tear",
     "You can be charged for the natural ageing of the home from ordinary use, which tenants usually aren't liable for.",
     "Add 'normal wear and tear excepted'.")
rule("MAINT_WEAR_TEAR_EXCEPTED", ["MAINTENANCE", "DEPOSIT"], r"\b(?:except|excepting|excluding|other than|save for|barring|subject to)\b" + S + r"\b(?:normal|reasonable|fair|ordinary) wear and tear\b|\b(?:normal|reasonable|fair|ordinary) wear and tear (?:excepted|exempted|being excepted)\b",
     FAV, "low", "Normal wear and tear excluded",
     "You aren't charged for ordinary ageing of the property.")
rule("MAINT_LANDLORD_MAJOR", ["MAINTENANCE"], r"\b" + L + r"\b" + S + r"\b(?:shall|will|agrees to)\b" + S + r"\b(?:major|structural|all)\b" + S + r"\brepairs?\b",
     FAV, "low", "Landlord handles major repairs",
     "The landlord is responsible for major or structural repairs, as is standard.")

# ---------- Penalty ----------
rule("PEN_HIGH_MONTHLY_INTEREST", ["PENALTY", "RENT"], r"\binterest\b" + S + r"(\d+(?:\.\d+)?)\s*(?:%|percent|per cent)\s*(?:per month|pm|a month|monthly|per mensem)",
     RISKY, "high", "High monthly interest on late payment",
     "Interest of 2% or more per month is 24%+ per year, far above normal lending rates.",
     "Ask for a modest flat late fee or a low annual interest rate.", value_min=2)
rule("PEN_DAILY", ["PENALTY"], r"\b(?:per day|each day|every day|daily|for each day)\b",
     RISKY, "medium", "Daily penalty",
     "Charges that accrue every day add up quickly, especially if a payment is delayed by a bank holiday or an emergency.",
     "Ask for a grace period and a capped one-time late fee.")
rule("PEN_MULTIPLE_RENT", ["PENALTY", "TERMINATION"], r"\b(?:double|twice|two times|2x|three times|triple|thrice)\b" + S + r"\b{R}\b|\b{R}\b" + S + r"\b(?:double|twice|two times|three times|triple)\b",
     RISKY, "high", "Penalty of multiple times the rent",
     "Overstaying or a breach costs double (or more) the rent, a penalty far larger than the landlord's actual loss.",
     "Replace with ordinary per-day rent for any overstay agreed in writing.")
rule("PEN_GRACE", ["PENALTY", "RENT"], r"\bgrace period\b|\bwithin a grace\b|\bdays of grace\b",
     FAV, "low", "Grace period for payment",
     "You get extra days to pay before any penalty applies.")

# ---------- Entry ----------
rule("ENTRY_ANYTIME", ["ENTRY"], r"\b(?:enter|entry|access|inspect\w*|visit)\b" + S + r"(?:\bat any (?:time|hour)\b|\bany time\b|\bwithout (?:any )?(?:prior )?notice\b|\bwith or without (?:prior )?notice\b|\bat all (?:times|reasonable times without))",
     RISKY, "high", "Landlord can enter without notice",
     "The landlord can come into your home whenever they like, which affects your privacy and security.",
     "Require at least 24 hours' written notice except in a genuine emergency.",
     unless=r"\bemergenc")
rule("ENTRY_DUPLICATE_KEY", ["ENTRY", "USE", "*"], r"\b(?:retain|keep|hold|have)\w*" + S + r"\b(?:duplicate|spare|extra|second|master) (?:set of )?keys?\b",
     RISKY, "medium", "Landlord keeps a key",
     "The landlord keeps a key to your home, so entry is possible without you knowing.",
     "Ask that keys be used only in emergencies or with your consent.")
rule("ENTRY_NOTICE", ["ENTRY"], r"\b(?:\d+|twenty[- ]four|forty[- ]eight|seventy[- ]two)\s*(?:\(\d+\)\s*)?hours?'?\s*(?:prior |advance )?(?:written )?notice\b|\breasonable (?:prior |advance )?(?:written )?notice\b|\bprior (?:written )?(?:notice|appointment|intimation)\b|\bwith the (?:prior )?(?:consent|permission) of the " + T + r"\b",
     FAV, "low", "Entry only with notice",
     "The landlord must give advance notice before entering, protecting your privacy.",
     unless=r"\bwithout (?:any )?(?:prior |advance )?(?:written )?notice\b|\bat any time\b")

# ---------- Liability ----------
rule("LIAB_BROAD_INDEMNITY", ["LIABILITY"], r"\bindemnif\w*" + S + r"\b(?:all|any|every)\b" + S + r"\b(?:loss(?:es)?|claims?|damages?|costs?|expenses?|liabilit)",
     RISKY, "medium", "Broad indemnity",
     "You agree to cover the landlord's losses or claims broadly, possibly including ones you did not cause.",
     "Limit the indemnity to losses caused by your negligence or breach of the agreement.",
     unless=r"\b(?:caused by|arising (?:out of|from)|due to|attributable to) (?:the )?(?:" + T + r"'?s? )?(?:negligence|default|breach|wilful)")
rule("LIAB_LANDLORD_EXEMPT", ["LIABILITY"], r"\b" + L + r"\b" + S + r"\b(?:shall not|will not|is not|not) (?:be )?(?:held )?(?:liable|responsible)\b" + S + r"\b(?:any|all)\b",
     RISKY, "medium", "Landlord excluded from all liability",
     "The landlord is not responsible for losses or injuries, even ones caused by poor upkeep of the building.",
     "Add an exception for loss caused by the landlord's negligence or failure to repair.",
     unless=r"\b(?:except|unless|save)\b" + S + r"\b(?:negligence|default|failure)")
rule("LIAB_FAULT_BASED", ["LIABILITY"], r"\b(?:caused by|arising (?:out of|from)|due to|attributable to)\b" + S + r"\b(?:negligence|default|breach|wilful)",
     FAV, "low", "Liability limited to fault",
     "Responsibility depends on who was actually at fault, which is fair to both sides.")

# ---------- Use ----------
rule("USE_GUEST_RESTRICTION", ["USE"], r"\b(?:guests?|visitors?|friends|relatives)\b" + S + r"(?:\bnot (?:be )?(?:allowed|permitted)\b|\bprohibited\b|\bprior (?:written )?(?:permission|consent|approval)\b|\bwithout (?:the )?(?:written )?(?:permission|consent)\b)|\bno (?:overnight )?(?:guests|visitors)\b",
     RISKY, "medium", "Restrictions on guests",
     "You need permission to have guests, which reaches into your private life in your own home.",
     "Limit restrictions to long-term additional occupants, not ordinary visitors.")
rule("USE_UNREASONABLY_WITHHELD", ["USE"], r"\bnot (?:to )?be unreasonably (?:withheld|refused|denied)\b",
     FAV, "low", "Consent can't be unreasonably refused",
     "The landlord must have a good reason to say no, which keeps the permission process fair.")

# ---------- Rent ----------
rule("RENT_CASH_NO_RECEIPT", ["RENT"], r"\bcash\b" + S + r"\b(?:no|without)\b" + S + r"\breceipts?\b|\bno receipts?\b",
     RISKY, "medium", "No proof of payment",
     "Paying without receipts leaves you with no proof that rent was paid if a dispute arises.",
     "Pay by bank transfer/UPI or insist on signed receipts.")
rule("RENT_RECEIPT", ["RENT"], r"\b" + L + r"\b" + S + r"\b(?:issue|provide|give|furnish)\w*" + S + r"\breceipts?\b",
     FAV, "low", "Rent receipts provided",
     "You get written proof of each payment.")
rule("RENT_LANDLORD_TAXES", ["RENT", "*"], r"\b" + T + r"\b" + S + r"\b(?:property tax|house tax|municipal tax(?:es)?)\b|\b(?:property tax|house tax|municipal tax(?:es)?)\b" + S + r"\b(?:borne|paid) by (?:the )?" + T + r"\b",
     RISKY, "medium", "Owner's taxes passed to you",
     "Property/municipal tax is normally the owner's liability; this clause shifts it to you.",
     "Ask that property and municipal taxes stay with the owner.")


# ================= Round 2: tuned on dev-set errors (data/clauses.csv only) =================
def upd(rid, **kw):
    for r in R:
        if r["id"] == rid:
            r.update(kw); return
    raise KeyError(rid)
NUMW = r"(\d{1,3}|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty|thirty)"

upd("GEN_SOLE_DISCRETION", pattern=r"\b(?:sole|absolute|exclusive|own)(?: and (?:absolute|exclusive))? discretion\b|\bas (?:he|she|they|it|the " + L + r") (?:may )?(?:deems?|thinks?|considers?) (?:fit|appropriate|necessary|proper)\b|\b(?:his|her|their|the " + L + r"'?s?) decision (?:shall|will) be final\b")
upd("GEN_OPEN_ENDED", pattern=r"\b(?:whatsoever|howsoever|irrespective of (?:the )?(?:cause|reason|circumstances?|fault)|however (?:small|minor|trivial)|of any (?:kind|nature) whatsoever)\b")
upd("GEN_UNILATERAL_AMEND", pattern=r"\b(?:modify|amend|change|alter|revise)\b" + S + r"\b(?:terms|rules|conditions|agreement|regulations)\b" + S + r"(?:at any time|unilaterally|without (?:the )?(?:tenant'?s? |lessee'?s? |licensee'?s? )?(?:consent|notice|approval))|\b" + L + r"\s+may\s+(?:unilaterally\s+)?(?:change|modify|amend|alter|revise)\b" + S + r"\b(?:terms|conditions|rules|agreement)\b|\bunilaterally (?:alter|change|modify|amend)")
upd("GEN_NO_LEGAL_RECOURSE", pattern=r"\b(?:shall not|cannot|will not|may not|agrees? not to|not to)\b" + S + r"\b(?:approach|move|file|go to|initiate)\b" + S + r"\b(?:court|tribunal|authority|legal proceedings?|rent controller)\b|\bwaives?\b" + S + r"\bright to (?:approach|move|file)")
upd("DEP_FORFEIT", types=["*"], pattern=r"\bforfeit|\bretain (?:the )?(?:entire|whole|full|complete) (?:security )?deposit\b")
upd("DEP_NO_TIMELINE", unless=r"\bwithin\s+(?:\w+\s*)?(?:\(\d+\)\s*)?(?:days?|weeks?|working days)\b|\bat the time of (?:handing over|vacating|handover)|\bon the (?:day|date) of (?:vacating|handing over|handover)|\bsimultaneously\b|\bimmediately\b|\bsame day\b|\bdue date\b|\bpay interest\b")
upd("TERM_LOCKIN", unless=r"\b(?:either party|both parties|neither party|mutual|binding on both)\b")
upd("TERM_PAY_REMAINDER", types=["*"])
upd("TERM_ONLY_LANDLORD", pattern=r"\bonly (?:the )?" + L + r"\b" + S + r"\bterminat|\b" + T + r"\s+(?:shall|will|may|can)\s*not\s+(?:be (?:entitled|allowed|permitted)\s+to\s+|have (?:the|any) right to\s+)?(?:terminat|cancel|end)\w*\b(?!" + S + r"\block[- ]?in)")
upd("TERM_SELF_HELP", pattern=r"\b(?:disconnect|cut off|stop|suspend)\w*" + S + r"\b(?:electricity|water|power|gas|supply|supplies)\b|\bchange the locks?\b|\block (?:up )?the (?:premises|flat|house)\b|\blocked out\b|\bremove (?:the )?(?:" + T + r"'?s? )?(?:belongings|possessions|articles)\b|\bforcibly\b|\btake (?:back )?possession\b" + S + r"\bwithout\b")
upd("TERM_MUTUAL", pattern=r"\b(?:either party|both parties|either of the parties|either side)\b" + S + r"\b(?:terminat|notice|vacat|end)|\b(?:terminat|notice)\w*" + S + r"\b(?:by )?(?:either party|both parties)\b")
upd("REN_AUTO", pattern=r"\bautomatic(?:ally)?\b" + S + r"\b(?:renew|extend|continu)|\b(?:renew|extend)\w*" + S + r"\bautomatic|\bauto[- ]?renew|\bdeemed (?:to (?:have been|be) )?(?:renewed|extended)\b|\bstand (?:automatically )?(?:renewed|extended)\b|\bshall continue\b" + S + r"\bunless\b" + S + r"\bnotice\b")
upd("REN_UNBOUNDED_INCREASE", pattern=r"\b(?:increase|enhance|escalat|hike|revis)\w*" + S + r"\b(?:as (?:decided|determined|fixed) by|at the (?:sole )?discretion|prevailing market|market rate|as (?:he|she|they|the " + L + r") (?:may )?(?:deems?|thinks?|considers?) fit|from time to time|whenever)\b|\b" + L + r"\s+(?:may|can|shall be entitled to)\s+(?:at any (?:time|point) )?(?:increase|revise|enhance|demand an increased)\b(?![^.]*(?:%|percent|per cent))|\b(?:fix|decide|determine)\w* any rent\b|\brent\b" + S + r"\bdecided by the " + L)
upd("REN_TENANT_OPTION", pattern=r"\b" + T + r"\s+(?:shall have|has|will have|is entitled to)\s+(?:the|an|a)\s+(?:first\s+)?(?:option|right)\s+to\s+(?:renew|extend)|\b" + T + r"\s+may,?\s+at (?:his|her|their|its) (?:sole )?option,?\s+(?:renew|extend)")
upd("MAINT_ALL_REPAIRS", pattern=r"\b" + T + r"\b" + S + r"\b(?:bear|pay|carry out|do|undertake|responsible for|liable for)\b" + S + r"\b(?:all|any|every)\b" + S + r"\b(?:repairs?|maintenance|replacement)\b|\ball (?:repairs|maintenance|replacements?)\b" + S + r"\b(?:borne|paid|responsibility|cost)\b" + S + r"\b" + T + r"\b",
    unless=r"\b(?:minor|day[- ]to[- ]day|small) (?:repairs|day)")
upd("MAINT_STRUCTURAL_TENANT", pattern=r"\b" + T + r"\b" + S + r"\b(?:repair|replace|bear|pay)\w*" + S + r"\b(?:structural|roof|foundation|walls?|pipelines?|wiring)\b|\b(?:structural|major)\b" + S + r"\b(?:borne|paid) by (?:the )?" + T + r"\b|\b(?:roof|structural|foundation|overhead (?:water )?tank|drainage|main (?:water|drainage|sewer)\w*)\b" + S + r"\b(?:responsibility of|borne by|paid by|done by|carried out by) (?:the )?" + T + r"\b")
upd("MAINT_WEAR_TEAR_INCLUDED", pattern=r"\b(?:including|irrespective of|regardless of|even if due to)\b" + S + r"\b(?:(?:normal|reasonable|fair|ordinary) (?:wear and tear|use)|ageing|aging|natural deterioration)\b")
upd("MAINT_LANDLORD_MAJOR", pattern=r"\b" + L + r"\b" + S + r"\b(?:shall|will|agrees to)\b" + S + r"\b(?:major|structural|all)\b" + S + r"\brepairs?\b|\b(?:major|structural)\b" + S + r"\b(?:by|borne by|responsibility of) (?:the )?" + L + r"\b|\b" + L + r"\b" + S + r"\bat (?:his|her|their|its) (?:own )?cost\b")
upd("PEN_MULTIPLE_RENT", types=["*"])
upd("ENTRY_ANYTIME", pattern=r"\b(?:enter|entry|access|inspect\w*|visit|show)\b" + S + r"(?:\bat any (?:time|hour)\b|\bany time\b|\bwithout (?:any )?(?:prior )?(?:notice|intimation|informing)\b|\bwith or without (?:prior )?notice\b|\bat all times\b|\bwhenever (?:he|she|they|it)? ?(?:wish|like|want|choose)e?s?\b)|\bsurprise (?:inspections?|visits?)\b|\bunrestricted access\b|\bfree access\b")
upd("ENTRY_NOTICE", pattern=r"\b(?:\d+|one|two|twenty[- ]four|forty[- ]eight|seventy[- ]two)\s*(?:\(\d+\)\s*)?(?:hours?|days?)'?s?\s*(?:prior |advance )?(?:written )?notice\b|\breasonable (?:prior |advance )?(?:written )?notice\b|\bprior (?:written )?(?:notice|appointment|intimation)\b|\bwith the (?:prior )?(?:consent|permission) of the " + T + r"\b|\bnot enter\b" + S + r"\bwithout\b" + S + r"\b(?:consent|permission|notice)\b|\bin the presence of the " + T)
upd("USE_GUEST_RESTRICTION", pattern=r"\b(?:guests?|visitors?|friends|relatives)\b" + S + r"(?:\bnot (?:be )?(?:allowed|permitted)\b|\bprohibited\b|\bprior (?:written )?(?:permission|consent|approval)\b|\bwithout (?:the )?(?:" + L + r"'?s? )?(?:prior )?(?:written )?(?:permission|consent|approval)\b)|\bno (?:overnight )?(?:guests|visitors)\b|\b(?:guests?|visitors)\b" + S + r"\bprohibited\b")
upd("RENT_CASH_NO_RECEIPT", pattern=r"\bcash\b" + S + r"\b(?:no|without|not)\b" + S + r"\b(?:receipts?|acknowledg\w*)\b|\bno (?:written )?(?:receipts?|acknowledgement)\b|\bnot (?:be )?(?:obliged|required|bound) to (?:issue|give|provide) (?:any )?receipts?\b")
upd("RENT_RECEIPT", pattern=r"\b" + L + r"\b" + S + r"\b(?:issue|provide|give|furnish|acknowledge)\w*" + S + r"\b(?:receipts?|payments?)\b|\b(?:receipt|register|acknowledg\w*)\b" + S + r"\bsigned by the " + L,
    unless=r"\bno (?:written )?(?:receipts?|acknowledg)|\bnot (?:be )?(?:obliged|required|bound)|\breceipt of which\b")

rule("GEN_UNCAPPED", ["*"], r"\bwithout (?:any )?(?:limit|cap|ceiling|upper limit)\b|\bunlimited\b",
     RISKY, "medium", "No upper limit",
     "The amount you can be asked to pay has no ceiling.",
     "Ask for a fixed cap on the amount.")
rule("GEN_LEGAL_COSTS", ["*"], r"\b" + T + r"\b" + S + r"\b(?:pay|bear|reimburse)\b" + S + r"\b" + L + r"'?s? (?:legal|litigation|advocate'?s?|lawyer'?s?) (?:costs|fees|expenses|charges)\b|\b" + T + r"\b" + S + r"\b(?:pay|bear)\b" + S + r"\b" + L + r"'?s? legal",
     RISKY, "medium", "You pay the landlord's legal costs",
     "You cover the landlord's lawyer fees, even when the landlord is in the wrong or the paperwork benefits them.",
     "Each party should bear its own legal costs, or costs should follow the outcome of a dispute.")
rule("GEN_ONE_SIDED_ARBITRATION", ["*"], r"\barbitrat\w*\b" + S + r"\b(?:appointed|nominated|chosen|selected)\b" + S + r"\b(?:solely|alone|only|exclusively)\b|\barbitrat\w*\b" + S + r"\b(?:solely|alone|only|exclusively)\b" + S + r"\b" + L + r"\b|\b" + L + r"\b" + S + r"\b(?:solely|alone|only) (?:appoint|nominate)",
     RISKY, "high", "Landlord picks the arbitrator",
     "Disputes go to an arbitrator chosen by the landlord alone, which is not a neutral forum.",
     "Ask for an arbitrator appointed jointly, or keep access to the Rent Authority/courts.")
rule("GEN_MUTUAL_AMEND", ["*"], r"\b(?:amendment|modification|change|variation)\w*" + S + r"\b(?:in writing|written)\b" + S + r"\b(?:signed by both|both parties|by both)\b",
     FAV, "low", "Changes need both signatures",
     "The agreement can only be changed with both parties' written signatures, so nothing changes behind your back.")
rule("GEN_CLEAR_TITLE", ["*"], r"\b" + L + r"\b" + S + r"\b(?:clear|marketable|absolute|valid) title\b",
     FAV, "low", "Landlord confirms ownership",
     "The landlord confirms they own the property and can rent it out, which protects you from a disputed tenancy.")
rule("RENT_ADVANCE", ["RENT", "DEPOSIT"], r"\b" + NUMW + r"\s*(?:\(\d+\)\s*)?months?'?\s*(?:rent|licen[cs]e fee)\b" + S + r"\bin advance\b|\bin advance\b" + S + r"\b" + NUMW + r"\s*months",
     RISKY, "medium", "Large advance rent",
     "Several months of rent are paid up front, so a lot of your money is locked in before you even move in.",
     "Limit advance rent to one month.", value_min=3)
rule("RENT_FIXED", ["RENT", "RENEWAL"], r"\brent\b" + S + r"\b(?:remain fixed|shall not be (?:revised|increased|enhanced)|not be increased)\b",
     FAV, "low", "Rent fixed for the term",
     "Your rent cannot go up during the agreement.")
rule("DEP_LARGE", ["DEPOSIT"], r"\bdeposit\b" + S + r"\b" + NUMW + r"\s*(?:\(\d+\)\s*)?months?'?",
     RISKY, "medium", "Deposit of several months' rent",
     "The deposit equals several months of rent, which is a lot of your money held by the landlord. India's Model Tenancy Act, 2021 suggests a cap of two months' rent for homes (only in states that have adopted it).",
     "Negotiate the deposit down to 2-3 months' rent.", value_min=3)
rule("DEP_CAPPED", ["DEPOSIT"], r"\bdeposit\b" + S + r"\b(?:not exceed|maximum of|capped at|limited to|no more than)\b",
     FAV, "low", "Deposit is capped",
     "The deposit amount is limited, keeping more of your money with you.")
rule("DEP_LATE_INTEREST", ["DEPOSIT"], r"\b" + L + r"\s+(?:shall|will)\s+pay\s+interest\b",
     FAV, "low", "Interest if the deposit is late",
     "The landlord pays you interest if the deposit is returned late, which encourages on-time refunds.")
rule("DEP_JOINT_INSPECTION", ["DEPOSIT", "MAINTENANCE"], r"\bjoint(?:ly)? inspect|\bjoint inspection\b|\binspect\w*" + S + r"\bin the presence of both\b",
     FAV, "low", "Joint inspection before deductions",
     "Damage is assessed together with you, so you can dispute claims on the spot.")
rule("TERM_SHORT_NOTICE", ["TERMINATION"], r"\b" + L + r"\b" + S + r"\b(?:terminat\w*|vacate|cancel\w*|revoke\w*|end)\b" + S + r"\b" + NUMW + r"\s*(?:\(\d+\)\s*)?(?:clear\s+)?days?\b",
     RISKY, "high", "Very short notice to vacate",
     "The landlord can end the tenancy with under a month's notice, which is very little time to find a new home.",
     "Ask for at least one month's written notice.", value_max=29, unless=r"\b(?:either party|both parties)\b|\bto (?:remedy|rectify|cure)\b")
rule("TERM_IMMEDIATE_VACATE", ["TERMINATION", "*"], r"\bvacate\b" + S + r"\bwithin\b" + S + r"\bhours?\b|\bvacate (?:forthwith|immediately)\b|\bimmediately (?:cancel|terminate|revoke)\b",
     RISKY, "high", "Must leave immediately",
     "You may have to leave within hours or immediately, with no time to find another home.",
     "Require at least 30 days' written notice and a chance to fix any breach.")
rule("TERM_FOR_CAUSE", ["TERMINATION"], r"\b" + L + r"\b" + S + r"\bterminat\w*" + S + r"\bonly (?:if|in case|on|upon|when)\b|\bopportunity to (?:remedy|rectify|cure)\b|\bnotice to (?:remedy|rectify|cure)\b",
     FAV, "low", "Landlord can end it only for a reason",
     "The landlord can only end the tenancy for a real breach, and you get a chance to fix it first.")
rule("TERM_NO_PENALTY_EXIT", ["TERMINATION"], r"\b" + T + r"\b" + S + r"\b(?:terminat|end|exit|vacate|leave)\w*" + S + r"\bwithout (?:any )?(?:penalty|charge|forfeiture)\b",
     FAV, "low", "Early exit without penalty",
     "You can leave early in the stated situations without paying a penalty.")
rule("MAINT_REPAINT", ["MAINTENANCE", "DEPOSIT"], r"\b" + T + r"\b" + S + r"\b(?:repaint\w*|re-paint\w*|get (?:the )?(?:entire )?(?:flat|premises|house|home) (?:re)?painted)\b|\b(?:regardless|irrespective) of (?:its|the|their) (?:condition|state)\b",
     RISKY, "medium", "Repainting regardless of condition",
     "You must pay for repainting whatever state the home is in. Repainting after normal use is usually the owner's cost.",
     "Make repainting conditional on damage beyond normal wear and tear.")
rule("MAINT_REPLACE_NEW", ["MAINTENANCE"], r"\b" + T + r"\b" + S + r"\breplace\b" + S + r"\bnew\b|\breplace\w*" + S + r"\b(?:appliances?|fixtures?|fittings?)\b" + S + r"\b(?:his|her|their|own) (?:cost|expense)",
     RISKY, "medium", "Replace items with new ones",
     "If something the landlord supplied breaks, even from age, you must buy a new one.",
     "Limit this to damage you caused; normal breakdowns should be the owner's cost.")
rule("MAINT_NOT_AT_FAULT", ["*"], r"\b" + T + r"\b" + S + r"\b(?:pay|bear|liable|responsible)\w*\b" + S + r"\b(?:natural calamit\w*|acts? of god|earthquake|flood|adjoining (?:flats?|premises)|neighbou?ring flats?)\b",
     RISKY, "high", "Liable for damage you didn't cause",
     "You pay for damage from events outside your control, such as natural disasters or leaks from neighbours.",
     "Limit your liability to damage caused by you, your family or guests.")
rule("MAINT_REPAIR_DEADLINE", ["MAINTENANCE"], r"\b" + L + r"\b" + S + r"\brepair\w*" + S + r"\bwithin\b|\bfailing which,? the " + T + r" may\b|\bdeduct the cost from the rent\b",
     FAV, "low", "Repairs within a deadline",
     "The landlord must fix problems within a set time, and you have a remedy if they don't.")
rule("LIAB_LANDLORD_LIABLE", ["LIABILITY"], r"\b" + L + r"\s+(?:shall|will) be (?:liable|responsible)\b",
     FAV, "low", "Landlord accepts liability",
     "The landlord takes responsibility for losses caused by the building's condition.")
rule("LIAB_PRIOR_DUES", ["*"], r"\bdues\b" + S + r"\b(?:pending|outstanding|arrears)\b" + S + r"\bbefore\b|\b(?:past dues|previous dues|dues pending from before)\b|\b(?:previous|earlier|former) (?:tenants?|occupants?|owners?)\b" + S + r"\b(?:dues|arrears|bills)\b",
     RISKY, "medium", "Pay dues from before you moved in",
     "You may be charged for unpaid bills or society dues that belong to an earlier period.",
     "Make dues before your move-in date the owner's responsibility.")
rule("USE_LIFESTYLE", ["USE", "*"], r"\bnot (?:cook|eat|consume)\b|\bnon[- ]?veg\w*\b" + S + r"\b(?:not|prohibited|banned)\b|\bopposite (?:gender|sex)\b|\bcurfew\b|\bbe (?:home|back|in) (?:by|before) \d+\s*(?:pm|am)?\b",
     RISKY, "medium", "Restrictions on your personal life",
     "The clause controls private choices (food, who visits, when you come home) that have nothing to do with protecting the property.",
     "Ask to remove lifestyle restrictions not tied to damage or nuisance.")
rule("USE_TENANT_PERMITTED", ["USE"], r"\b" + T + r"\s+may\s+(?:have|receive|invite|install|work|keep (?:a|one))\b",
     FAV, "low", "Explicit freedom of use",
     "The agreement confirms things you are allowed to do, avoiding later disputes.")

# ================= Round 3: aligned with the annotator's policy + patterns missed on real agreements =================
# Policy: refunds "on vacating" without a day count and 10% renewal increases are customary -> not flagged.
R[:] = [r for r in R if r["id"] != "DEP_NO_TIMELINE"]
upd("REN_RENT_INCREASE_HIGH", value_min=11,
    explanation="The rent rises by more than 10%, above the increases customary on renewal (often around 5-10%).")
rule("TERM_ON_ANY_BREACH", ["TERMINATION", "PENALTY", "*"],
     r"\b(?:fail\w*|default\w*|breach\w*|violat\w*|non-?compliance|contravene\w*)\b" + S + r"\b(?:automatic(?:ally)? terminat\w*|stand terminated|immediate(?:ly)? terminat\w*|terminat\w* (?:immediately|forthwith|automatically)|(?:cause|grounds?) for (?:immediate )?termination|self[- ]?evict\w*|vacate (?:immediately|forthwith))"
     + r"|\b(?:automatic(?:ally)? terminat\w*|stand terminated|cause for (?:immediate )?termination|grounds? for termination)\b" + S + r"\b(?:fail\w*|default\w*|breach\w*|violat\w*|non-?compliance)\b",
     RISKY, "high", "Ended for any breach",
     "The agreement can end automatically or immediately for any failure to comply, however small, with no notice or chance to fix it.",
     "Limit termination to serious breaches, after written notice and at least 15-30 days to remedy.",
     unless=r"\b(?:notice to (?:remedy|rectify|cure)|opportunity to (?:remedy|rectify|cure)|after (?:giving|serving)\b[^.;]*?\bnotice|days'? (?:written )?notice to)\b")
rule("MAINT_TENANT_REPAIR_REPLACE", ["MAINTENANCE", "*"],
     r"\b" + T + r"\b" + S + r"\b(?:responsible|liable)\b" + S + r"\b(?:repair\w*|replac\w*)\b(?!" + S + r"\b(?:caused by|due to|resulting from|arising from)\b)",
     RISKY, "medium", "You repair or replace items",
     "You must pay to repair or replace fixtures and appliances, which may include breakdowns from age or normal use.",
     "Limit this to damage caused by you or your guests; normal breakdowns should be the owner's cost.",
     unless=r"\b(?:minor|day[- ]to[- ]day|small)\b|\b(?:caused by|due to|resulting from)\b" + S + r"\b(?:negligence|misuse|carelessness|wilful)\b|\bwear and tear\b")
rule("GEN_ATTORNEY_FEES", ["*"],
     r"\b" + T + r"\b" + S + r"\b(?:pay|bear|reimburse|liable for)\b" + S + r"\b(?:attorney'?s?'?|lawyer'?s?'?|advocate'?s?'?|legal|collection)\s+(?:fees|costs|charges|expenses)\b",
     RISKY, "medium", "You pay legal or collection costs",
     "You must pay the landlord's lawyer or collection costs, which can add up quickly in any dispute.",
     "Each party should bear its own legal costs, or costs should follow the outcome.",
     unless=r"\b(?:each party|both parties|prevailing party|equally)\b")
upd("RENT_ADVANCE", pattern=r"\b" + NUMW + r"\s*(?:\(\d+\)\s*)?months?'?\s*(?:rent|licen[cs]e fee)\b" + S + r"\bin advance\b|\bin advance\b" + S + r"\b" + NUMW + r"\s*months|\badvance\b" + S + r"\b(?:equivalent to|equal to|of)\s+" + NUMW + r"\s*(?:\(\d+\)\s*)?months?'?\s*(?:rent|licen[cs]e fee)")

placeholders = {
    "T": r"(?:tenants?|lessees?|licensees?)",
    "L": r"(?:landlords?|lessors?|licensors?|owners?)",
    "S": r"[^.;]*?",
    "R": r"(?:rent|rental|licen[cs]e fees?)",
}

out = {
    "version": 1,
    "notes": "Shared by the Python pipeline and the browser demo. Patterns are case-insensitive and must stay compatible with both Python 're' and JavaScript RegExp (no lookbehind, no named groups). Placeholders {T}, {L}, {S} are expanded at load time. 'unless' suppresses a rule; 'value_min'/'value_max' compare capture group 1 (digits or number words).",
    "placeholders": placeholders,
    "risk_labels": {"RISKY": "Risky", "NEUTRAL": "Neutral", "TENANT_FAVORABLE": "Tenant-favourable"},
    "severity_weight": {"high": 3, "medium": 2, "low": 1},
    "clause_types": clause_types,
    "rules": R,
}
json.dump(out, open(sys.argv[1], "w"), indent=2, ensure_ascii=False)
print(len(R), "rules")
