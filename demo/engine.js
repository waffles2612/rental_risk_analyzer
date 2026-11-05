"use strict";
// ---------- Rule book (shared rules.json, same semantics as rental_risk/rules.py) ----------
const expand = p => Object.entries(RULES.placeholders).reduce((s, [k, v]) => s.split("{" + k + "}").join(v), p);
const BOOK = {
  types: Object.fromEntries(Object.entries(RULES.clause_types).map(([t, spec]) => [t, spec.keywords.map(([p, w]) => [new RegExp(p, "gi"), w])])),
  rules: RULES.rules.map(r => ({ ...r, rx: new RegExp(expand(r.pattern), "i"), rxg: new RegExp(expand(r.pattern), "gi"),
    unlessRx: r.unless ? new RegExp(expand(r.unless), "i") : null, types: new Set(r.types) })),
};
const RISKY = "RISKY", NEUTRAL = "NEUTRAL", FAV = "TENANT_FAVORABLE";
const LABEL = { RISKY: "Risky", NEUTRAL: "Neutral", TENANT_FAVORABLE: "Tenant-favourable" };
const SEV = { high: 3, medium: 2, low: 1, "": 0 };
const NUMWORDS = { a: 1, an: 1, one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9, ten: 10,
  eleven: 11, twelve: 12, fifteen: 15, twenty: 20, thirty: 30, "forty five": 45, sixty: 60, ninety: 90 };

function normalize(t) {
  t = t.replace(/[‘’]/g, "'").replace(/[“”]/g, '"');
  t = t.replace(/\b(rs|no|nos|mr|mrs|ms|dr|smt|shri|sri|st|viz|vs|etc|ltd|pvt|approx|sq|ft)\./gi, "$1");
  t = t.replace(/\bi\.e\./gi, "ie").replace(/\be\.g\./gi, "eg").replace(/\bp\.\s?([am])\./gi, "p$1");
  t = t.replace(/(\d)\.(\d)/g, "$1·$2").replace(/\/-/g, "");
  return t.replace(/\s+/g, " ").trim();
}
function num(s) {
  if (s == null) return null;
  const w = s.trim().toLowerCase();
  if (w in NUMWORDS) return NUMWORDS[w];
  const v = parseFloat(w.replace("·", ".").replace(/,/g, ""));
  return isNaN(v) ? null : v;
}
function classifyType(text) {
  const norm = normalize(text);
  const head = norm.slice(0, 60).includes(":") ? norm.slice(0, 60).split(":")[0] : "";
  const scores = {};
  for (const [t, kws] of Object.entries(BOOK.types)) {
    let s = 0;
    for (const [rx, w] of kws) {
      const n = (norm.match(rx) || []).length;
      if (n) { s += w * Math.min(n, 3); if (head && (head.match(rx) || []).length) s += w * 2; }
    }
    scores[t] = s;
  }
  let best = "OTHER", bs = 0;
  for (const [t, s] of Object.entries(scores)) if (s > bs) { best = t; bs = s; }
  return [best, scores];
}
function secondBest(scores) {
  const r = Object.entries(scores).sort((a, b) => b[1] - a[1]);
  return r.length > 1 && r[1][1] > 0 && r[1][1] >= 0.5 * r[0][1] ? r[1][0] : null;
}
function matchRules(text, ctype, secondary) {
  const norm = normalize(text), hits = [], seen = new Set();
  for (const r of BOOK.rules) {
    if (!r.types.has("*") && !r.types.has(ctype) && !(secondary && r.types.has(secondary))) continue;
    const m = norm.match(r.rx);
    if (!m) continue;
    if (r.unlessRx && r.unlessRx.test(norm)) continue;
    if (r.value_min != null || r.value_max != null) {
      const vals = [];
      for (const mm of norm.matchAll(r.rxg)) { const g = mm.slice(1).find(x => x); const v = num(g); if (v != null) vals.push(v); }
      if (!vals.length) continue;
      if (r.value_min != null && Math.max(...vals) < r.value_min) continue;
      if (r.value_max != null && Math.min(...vals) > r.value_max) continue;
    }
    if (seen.has(r.id)) continue;
    seen.add(r.id);
    hits.push({ rule_id: r.id, risk: r.risk, severity: r.severity, title: r.title, explanation: r.explanation, ask: r.ask || "",
      evidence: m[0].replace(/·/g, ".").slice(0, 160) });
  }
  return hits;
}
const riskFromHits = h => h.some(x => x.risk === RISKY) ? RISKY : h.some(x => x.risk === FAV) ? FAV : NEUTRAL;

// ---------- Segmentation (mirrors rental_risk/ingest.py) ----------
const NUM_START = /^\s*(?:((?:clause|article|section)\s+[\dIVXivx]+[.:)]?)|(\d{1,2}(?:\.\d{1,2}){0,3}[.)]|\d{1,2}(?:\.\d{1,2}){1,3})(?=\s+\S)|(\(?[a-hj-z]\)|\([ivx]{1,4}\)|[ivx]{1,4}[.)])(?=\s+\S))\s*/i;
const HEADING = /^\s*(?:[A-Z][A-Z0-9 &\/,'()-]{2,60}|[A-Z][a-zA-Z &\/,'-]{2,40}:)\s*$/;
const INLINE_HEADING = /^\s*([A-Z][A-Za-z &\/'-]{2,40}?)\s*[:–—-]\s+(?=[A-Z])/;
const END_OF_TERMS = /^\s*(?:in witness where(?:of|to)|signed (?:sealed )?and delivered|witnesses?\s*[:1]|schedule\s+[a-z0-9]*\s*$)/i;
const BOILERPLATE = /^(?:witness(?:es)?|signature|signed|landlord|tenant|lessor|lessee|licensor|licensee|date|place|name)\b.{0,40}$/i;
const SMALL = new Set(["and", "of", "the", "to", "for", "in", "on", "by", "with", "a", "an", "&", "or"]);
function isHeadingText(rest) {
  const words = rest.replace(/:$/, "").split(/\s+/).filter(Boolean);
  if (!words.length || rest.length >= 45 || words.length > 6 || /[.;,]$/.test(rest)) return false;
  if (SMALL.has(words[words.length - 1].toLowerCase())) return false;
  return words.every(w => /^[A-Z]/.test(w) || SMALL.has(w.toLowerCase()) || !/^[A-Za-z]/.test(w));
}
const titleCase = s => s.toLowerCase().replace(/\b[a-z]/g, c => c.toUpperCase());
const splitSentences = t => t.replace(/([.;])\s+(?=[A-Z(])/g, "$1\u0001").split("\u0001");

const ABBR = new Set(["mr", "mrs", "ms", "dr", "rs", "no", "nos", "smt", "shri", "sri", "st", "s/o", "d/o", "w/o", "viz", "vs", "etc",
  "ltd", "pvt", "co", "sq", "ft", "approx", "sl", "dt", "ref", "inr", "re", "rd", "opp", "nr", "ph", "e.g", "i.e"]);
const BOUNDARY = /[.;]\s+(?=[A-Z("'\u201c])/g;
const PAGE_MARK = /^\s*-\s*\d{1,3}\s*-\s*/;
const MAX_CLAUSE = 500, MIN_PIECE = 60;
function splitLong(text, maxLen = MAX_CLAUSE) {
  if (text.length <= maxLen) return [text];
  const pieces = []; let start = 0;
  for (const m of text.matchAll(BOUNDARY)) {
    const before = text.slice(start, m.index).split(/\s+/).filter(Boolean);
    const last = before.length ? before[before.length - 1].toLowerCase().replace(/^[("']+|[("']+$/g, "") : "";
    if (ABBR.has(last) || last.length <= 1 || /^(?:[a-z]\.)+[a-z]?$/.test(last)) continue;
    pieces.push(text.slice(start, m.index + 1).trim());
    start = m.index + m[0].length;
  }
  pieces.push(text.slice(start).trim());
  const out = [];
  for (const p of pieces) { if (out.length && out[out.length - 1].length < MIN_PIECE) out[out.length - 1] += " " + p; else out.push(p); }
  if (out.length > 1 && out[out.length - 1].length < MIN_PIECE) { const l = out.pop(); out[out.length - 1] += " " + l; }
  return out.filter(Boolean);
}
function joinWrapped(lines) {
  const out = [];
  for (const ln of lines) {
    if (out.length && !/[.;:]\s*$/.test(out[out.length - 1]) && /^[a-z0-9(]/.test(ln)) out[out.length - 1] += " " + ln;
    else out.push(ln);
  }
  return out;
}
function segment(text, minChars = 30) {
  text = text.replace(/\r\n?/g, "\n").replace(/ /g, " ");
  const lines = text.split("\n").map(l => l.replace(PAGE_MARK, "").replace(/\s+$/, ""));
  const raw = [];
  const starts = lines.filter(l => NUM_START.test(l)).length;
  if (starts >= 3) {
    let curNum = "", curHead = "", buf = [], pending = "";
    for (const ln of lines) {
      if (!ln.trim() || /^\s*(?:page\s*)?\d+(?:\s*of\s*\d+)?\s*$/i.test(ln)) continue;
      if (END_OF_TERMS.test(ln)) break;
      const m = ln.match(NUM_START);
      if (m) {
        if (buf.length) raw.push([curNum, curHead, buf.join(" ")]);
        const rest = ln.slice(m[0].length).trim();
        if (isHeadingText(rest)) { curNum = ""; curHead = ""; buf = []; pending = rest.replace(/:$/, ""); continue; }
        curNum = (m[1] || m[2] || m[3] || "").trim().replace(/[.:]+$/, "");
        curHead = pending; buf = [rest];
        if (!/^\d+\.\d+/.test(curNum)) pending = "";
      } else if (HEADING.test(ln) && ln.trim().length < 60) {
        if (buf.length) { raw.push([curNum, curHead, buf.join(" ")]); curNum = ""; curHead = ""; buf = []; }
        pending = ln.trim().replace(/:$/, "");
      } else buf.push(ln.trim());
    }
    if (buf.length) raw.push([curNum, curHead, buf.join(" ")]);
  } else {
    let paras = text.split(/\n\s*\n/).map(p => p.trim()).filter(Boolean);
    if (paras.length < 3) {
      const ls = joinWrapped(lines.map(l => l.trim()).filter(Boolean));
      if (ls.length >= 3 && ls.reduce((s, l) => s + l.length, 0) / ls.length >= 40) paras = ls;  // one clause per line
      else paras = splitSentences(paras.join(" ")).filter(s => s.trim());
    }
    let pending = "";
    for (let p of paras) {
      p = p.split("\n").map(x => x.trim()).join(" ").replace(/^[-*\u2022]\s+/, "");
      if (END_OF_TERMS.test(p)) break;
      if (HEADING.test(p) && p.length < 60) { pending = p.replace(/:$/, ""); continue; }
      raw.push(["", pending, p]); pending = "";
    }
  }
  const out = [];
  for (let [n, head, body] of raw) {
    body = body.replace(/\s+/g, " ").trim();
    if (!head) {
      const m = body.match(INLINE_HEADING);
      if (m && m[1].split(/\s+/).length <= 5) { head = m[1].trim(); body = body.slice(m[0].length).trim(); }
    }
    head = head && head === head.toUpperCase() ? titleCase(head) : head;
    splitLong(body).forEach((piece, k) => {
      if (piece.length < minChars || BOILERPLATE.test(piece)) return;
      out.push({ index: out.length + 1, number: n, heading: k === 0 ? head : "", text: piece });
    });
  }
  return out;
}

// ---------- Document-level checks (mirrors rental_risk/doccheck.py) ----------
const DURATION = /\b(\d{1,3}|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty|thirty|forty[- ]five|sixty|ninety|a|an)\s*(?:\(\s*\d{1,3}\s*\)\s*)?(?:clear\s+|calendar\s+|working\s+)?(day|week|month|year)s?\b/gi;
const UNIT = { day: 1, week: 7, month: 30, year: 365 };
const MONEY = /(?:rs|inr|₹|\$|usd|£|€|rupees)\s*\.?\s*([\d,]+(?:[.·]\d+)?)/gi;
const T_ = "(?:tenants?|lessees?|licensees?)", L_ = "(?:landlords?|lessors?|licensors?|owners?)";
function durations(t) {
  const out = [];
  for (const m of t.matchAll(DURATION)) {
    const raw = m[1].toLowerCase().replace("-", " ");
    const n = /^\d+$/.test(raw) ? parseInt(raw, 10) : NUMWORDS[raw];
    if (n) out.push(n * UNIT[m[2].toLowerCase()]);
  }
  return out;
}
function amounts(t) {
  const out = [];
  for (const m of t.matchAll(MONEY)) { const v = parseFloat(m[1].replace(/,/g, "").replace("·", ".")); if (!isNaN(v) && v >= 100) out.push(v); }
  return out;
}
function monthsMultiple(t) {
  const m = t.match(/\b(\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s*(?:\(\s*\d+\s*\)\s*)?months?'?\s*(?:of\s+)?(?:the\s+)?(?:monthly\s+)?(?:rent|rental|license fee)/i);
  return m ? num(m[1]) : null;
}
function partyForNotice(s) {
  s = s.toLowerCase();
  if (/\b(?:either party|both parties|either of the parties|each party)\b/.test(s)) return "both";
  if (new RegExp("notice\\s+(?:from|by|given by|issued by|served by)\\s+(?:the\\s+)?" + L_).test(s)) return "landlord";
  if (new RegExp("notice\\s+(?:from|by|given by|issued by|served by)\\s+(?:the\\s+)?" + T_).test(s)) return "tenant";
  const t = s.search(new RegExp("\\b" + T_ + "\\b")), l = s.search(new RegExp("\\b" + L_ + "\\b"));
  if (t >= 0 && (l < 0 || t < l)) return "tenant";
  return l >= 0 ? "landlord" : null;
}
function documentChecks(clauses) {
  const f = [], byType = {};
  for (const c of clauses) (byType[c.clause_type] = byType[c.clause_type] || []).push(c);
  let rent = null, rentIdx = null;
  for (const c of [...(byType.RENT || []), ...clauses.filter(c => c.clause_type !== "RENT")]) {
    const t = normalize(c.text);
    if (/\b(?:rent|license fee)\b/i.test(t) && /\bmonth|\bper mensem\b|\bpm\b/i.test(t)) {
      const a = amounts(t);
      if (a.length && !t.toLowerCase().slice(0, 80).includes("deposit")) { rent = a[0]; rentIdx = c.index; break; }
    }
  }
  for (const c of byType.DEPOSIT || []) {
    const t = normalize(c.text);
    if (monthsMultiple(t) != null || !rent) continue;
    const a = amounts(t);
    if (!a.length) continue;
    const mult = a[0] / rent;
    if (mult > 2.0001) f.push({ check_id: "DOC_DEPOSIT_RATIO", risk: RISKY, severity: mult >= 5 ? "high" : "medium",
      title: `Deposit is about ${mult.toFixed(1)}× the monthly rent`,
      explanation: `The security deposit equals roughly ${mult.toFixed(1)} months of rent. That is a lot of your money held by the landlord, and it is harder to recover in a dispute. For reference, India's Model Tenancy Act, 2021 suggests a cap of two months' rent for residential premises (it applies only in states that have adopted it).`,
      ask: "Negotiate the deposit down to 2-3 months' rent, or ask for interest on the excess.", clause_indexes: [c.index, rentIdx].filter(Boolean).sort((x, y) => x - y) });
    break;
  }
  const tn = [], ln = [];
  for (const c of [...(byType.TERMINATION || []), ...(byType.RENEWAL || [])]) {
    for (const s of splitSentences(normalize(c.text))) {
      if (!s.toLowerCase().includes("notice")) continue;
      const d = durations(s);
      if (!d.length) continue;
      const p = partyForNotice(s), v = Math.min(...d);
      if (p === "tenant" || p === "both") tn.push([v, c.index]);
      if (p === "landlord" || p === "both") ln.push([v, c.index]);
    }
  }
  if (tn.length && ln.length) {
    const t = tn.reduce((a, b) => b[0] > a[0] ? b : a), l = ln.reduce((a, b) => b[0] < a[0] ? b : a);
    if (t[0] > l[0]) f.push({ check_id: "DOC_NOTICE_ASYMMETRY", risk: RISKY, severity: "high", title: "You must give more notice than the landlord",
      explanation: `You have to give about ${t[0]} days' notice to leave, but the landlord only has to give about ${l[0]} days. The termination terms are tilted against you.`,
      ask: "Ask for the same notice period for both parties.", clause_indexes: [...new Set([t[1], l[1]])].sort((a, b) => a - b) });
  }
  if (ln.length) {
    const l = ln.reduce((a, b) => b[0] < a[0] ? b : a);
    if (l[0] < 30) f.push({ check_id: "DOC_SHORT_NOTICE", risk: RISKY, severity: l[0] <= 15 ? "high" : "medium", title: `Only ${l[0]} days' notice to vacate`,
      explanation: `The landlord can ask you to leave with only about ${l[0]} days' notice, which is very little time to find a new home.`,
      ask: "Ask for at least one month's written notice.", clause_indexes: [l[1]] });
  }
  const expected = {
    DEPOSIT: ["No security-deposit clause", "Nothing says how much deposit is held, when it is returned, or what can be deducted."],
    TERMINATION: ["No termination / notice clause", "Nothing says how either side can end the agreement or how much notice is needed."],
    MAINTENANCE: ["No repairs clause", "Nothing says who pays for repairs. That ambiguity usually ends up costing the tenant."],
  };
  for (const [t, [title, expl]] of Object.entries(expected))
    if (!byType[t]) f.push({ check_id: "DOC_MISSING_" + t, risk: RISKY, severity: "low", title, explanation: expl, ask: "Ask for this to be added in writing before signing.", clause_indexes: [] });
  return f;
}

// ---------- Explanation + pipeline (mirrors rental_risk/pipeline.py, rules engine) ----------
function keyFacts(text) {
  const t = normalize(text), facts = [];
  for (const d of [...new Set(durations(t))].sort((a, b) => a - b)) facts.push(d >= 30 && d % 30 === 0 ? `${d / 30} month(s)` : `${d} day(s)`);
  for (const a of amounts(t).slice(0, 3)) facts.push("₹" + a.toLocaleString("en-IN", { maximumFractionDigits: 0 }));
  for (const m of [...t.matchAll(/(\d+(?:[.·]\d+)?)\s*(?:%|percent|per cent)/gi)].slice(0, 3)) facts.push(m[1].replace("·", ".") + "%");
  return facts.slice(0, 6);
}
function explain(risk, hits, facts) {
  const r = hits.filter(h => h.risk === RISKY).sort((a, b) => SEV[b.severity] - SEV[a.severity]);
  const f = hits.filter(h => h.risk === FAV);
  if (risk === RISKY) {
    const parts = r.slice(0, 2).map(h => h.explanation);
    if (facts.length) parts.push("Key numbers: " + facts.join(", ") + ".");
    return [r[0].severity, parts.join(" "), r[0].ask || ""];
  }
  if (risk === FAV) return ["low", f.slice(0, 2).map(h => h.explanation).join(" "), ""];
  return ["", "Standard clause; no risk indicators found.", ""];
}
const FOLD = new Set(["DOC_NOTICE_ASYMMETRY", "DOC_DEPOSIT_RATIO", "DOC_SHORT_NOTICE"]);
function analyze(text) {
  const clauses = segment(text).map(c => {
    const full = c.heading ? `${c.heading}: ${c.text}` : c.text;
    const [ctype, scores] = classifyType(full);
    const hits = matchRules(full, ctype, secondBest(scores));
    const facts = keyFacts(full), risk = riskFromHits(hits);
    const [severity, explanation, ask] = explain(risk, hits, facts);
    return { ...c, clause_type: ctype, type_label: (RULES.clause_types[ctype] || { label: "Other" }).label, risk, severity, findings: hits, explanation, ask, key_facts: facts };
  });
  if (clauses.some(c => c.findings.some(h => h.rule_id === "DEP_TIMELINE")))
    for (const c of clauses) {
      const n = c.findings.length;
      c.findings = c.findings.filter(h => h.rule_id !== "DEP_NO_TIMELINE");
      if (c.findings.length !== n) { c.risk = riskFromHits(c.findings); [c.severity, c.explanation, c.ask] = explain(c.risk, c.findings, c.key_facts); }
    }
  const byIdx = Object.fromEntries(clauses.map(c => [c.index, c]));
  const doc = [];
  for (const f of documentChecks(clauses)) {
    if (f.check_id === "DOC_SHORT_NOTICE" && clauses.some(c => c.findings.some(h => h.rule_id === "TERM_SHORT_NOTICE" || h.rule_id === "TERM_IMMEDIATE_VACATE"))) continue;
    doc.push(f);
    if (!FOLD.has(f.check_id)) continue;
    for (const i of f.clause_indexes) {
      const c = byIdx[i];
      if (!c || c.findings.some(h => h.rule_id === f.check_id) || (f.check_id === "DOC_DEPOSIT_RATIO" && c.clause_type !== "DEPOSIT")) continue;
      c.findings.push({ rule_id: f.check_id, risk: RISKY, severity: f.severity, title: f.title, explanation: f.explanation, ask: f.ask, evidence: "" });
      c.risk = RISKY; [c.severity, c.explanation, c.ask] = explain(RISKY, c.findings, c.key_facts);
    }
  }
  const counts = { RISKY: 0, NEUTRAL: 0, TENANT_FAVORABLE: 0 }, sev = { high: 0, medium: 0, low: 0 };
  for (const c of clauses) { counts[c.risk]++; if (c.risk === RISKY) sev[c.severity || "medium"]++; }
  for (const f of doc) if (f.risk === RISKY) sev[f.severity]++;
  const score = Object.entries(sev).reduce((s, [k, v]) => s + RULES.severity_weight[k] * v, 0);
  const rating = sev.high >= 3 || score >= 14 ? "High" : score >= 5 ? "Moderate" : "Low";
  return { clauses, doc, summary: { counts, sev, score, rating } };
}

