"""Test the dashboard's generated text under every filter combination.

Run:  python src/check_narrative.py      (needs playwright + chromium)

Every takeaway, chart title and Summary headline is generated from the numbers on
screen. This renders all six tabs for every combination of window (3) x attendance
definition (2) x outlier toggle (2) x segment (7) x tier (4) x region (4) = 1,344
filter states, plus every firm's detail view, and checks the rendered text:

  1. hygiene    - no NaN / undefined / Infinity / empty fragments, no "1 firms"
  2. agreement  - words match the numbers next to them, parsed from the text itself
                  (independent of the code that wrote the sentence):
                  "beat it (A vs B)" needs A > B, "fell short of it" needs A < B,
                  "more often (A vs B)" needs A > B, "less often" needs A < B,
                  "went from A% to B% (+C pts)" needs C = B - A, "X of Y" needs X <= Y
  3. stability  - the recommendations read identically in every filter state
Exits non-zero if any check fails, printing each distinct failure once with an example state.
"""
import sys
from collections import OrderedDict
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent

JS = r"""
() => {
  const pct = s => parseFloat(s.replace("−", "-"));
  const checks = [
    [/NaN|undefined|Infinity|\[object|\bnull\b/, () => "broken value in text"],
    [/(?<!Tier )(?<![\d.,$])\b1 (firms|deals|attendances|meetings|events|contacts|live deals)\b/, () => "plural after 1"],
    [/\(\s*\)|,\s*\.|\s\.(\s|$)|against\s*\.|predict,\s*\.|\.\./, () => "empty fragment / punctuation"],
    [/\b(rose|risen|gained|increased) −\d/, () => "'rose' with a negative change"],
    [/\b(fell|dropped) \+\d/, () => "'fell' with a positive change"],
  ];
  const pairChecks = [
    [/\bbeat(?: it)? \((\d+)% vs (\d+)%\)/g, (a, b) => a > b, "'beat' but first number not higher"],
    [/fell short of(?: it| its prediction)? \((\d+)%(?: vs (\d+)%)?\)/g, (a, b) => isNaN(b) || a < b, "'fell short' but first number not lower"],
    [/\bmore often \((\d+)% vs (\d+)%\)/g, (a, b) => a > b, "'more often' but first number not higher"],
    [/\bless often \((\d+)% vs (\d+)%\)/g, (a, b) => a < b, "'less often' but first number not lower"],
    [/\babout as often \((\d+)% vs (\d+)%\)/g, (a, b) => Math.abs(a - b) <= 6, "'about as often' but numbers differ by more than 5 pts"],
  ];
  const out = [];
  const scan = (txt, state) => {
    for (const [re, msg] of checks) { const m = txt.match(re); if (m) out.push([msg(), state, txt.slice(Math.max(0, m.index - 60), m.index + 80)]); }
    for (const [re, ok, msg] of pairChecks) for (const m of txt.matchAll(re)) { const a = pct(m[1]), b = pct(m[2]); if (!ok(a, b)) out.push([msg, state, m[0]]); }
    for (const m of txt.matchAll(/went from (\d+)% to (\d+)% \(([+−]\d+) pts\)/g)) { if (Math.abs(pct(m[2]) - pct(m[1]) - pct(m[3])) > 1) out.push(["'went from A to B (C pts)' does not add up", state, m[0]]); }
    for (const m of txt.matchAll(/\b(\d+) of (\d+)\b/g)) { if (+m[1] > +m[2]) out.push(["'X of Y' with X > Y", state, m[0]]); }
  };
  const tabs = ["summary", "happened", "outcomes", "learn", "firms", "methods"];
  const segs = ["All", ...new Set(D.firms.map(f => f.segment))], tiers = ["All", "Tier 1", "Tier 2", "Tier 3"], regs = ["All", ...new Set(D.firms.map(f => f.coverage_region))];
  let states = 0, recsDefault = null;
  Object.assign(S, { w: 60, def: "confirmed", out: 1, seg: "All", tier: "All", region: "All", tab: "summary" }); syncControls(); RENDER.summary();
  recsDefault = document.querySelector("#summary .recs").innerText;
  for (const w of [30, 60, 90]) for (const def of ["confirmed", "incl_tentative"]) for (const o of [1, 0])
    for (const seg of segs) for (const tier of tiers) for (const region of regs) {
      Object.assign(S, { w, def, out: o, seg, tier, region, focus: null, firm: null, q: "" });
      const state = `w=${w} def=${def} out=${o} seg=${seg} tier=${tier} region=${region}`;
      for (const t of tabs) { S.tab = t;
        try { syncControls(); RENDER[t](); } catch (e) { out.push(["render error: " + e.message, state + " tab=" + t, ""]); continue; }
        scan(document.getElementById(t).innerText.replace(/\s+/g, " "), state + " tab=" + t);
        if (t === "summary" && document.querySelector("#summary .recs").innerText !== recsDefault) out.push(["recommendations changed under filters", state, ""]); }
      states++;
    }
  // every firm's detail view at each window
  for (const w of [30, 60, 90]) for (const f of D.firms) {
    Object.assign(S, { w, def: "confirmed", out: 1, seg: "All", tier: "All", region: "All", focus: null, q: "", firm: f.firm_id, tab: "firms" });
    try { renderFirms(); } catch (e) { out.push(["firm view error: " + e.message, `w=${w} firm=${f.firm_id}`, ""]); continue; }
    scan(document.getElementById("firms").innerText.replace(/\s+/g, " "), `w=${w} firm=${f.firm_id}`); }
  return { states, issues: out };
}
"""


def main():
    with sync_playwright() as p:
        pg = p.chromium.launch().new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto((ROOT / "dashboard" / "index.html").as_uri())
        pg.set_default_timeout(0)
        res = pg.evaluate(JS)
    distinct = OrderedDict()
    for msg, state, ctx in res["issues"]:
        key = (msg, ctx[:70])
        distinct.setdefault(key, [0, state, ctx]); distinct[key][0] += 1
    print(f"Filter states rendered: {res['states']} (x6 tabs) + 180 firm views")
    print(f"Issues: {len(res['issues'])} total, {len(distinct)} distinct")
    for (msg, _), (n, state, ctx) in distinct.items():
        print(f"\n- {msg}  [{n}x]  e.g. {state}\n    …{ctx}…")
    print("page errors:", errs or "none")
    sys.exit(1 if res["issues"] or errs else 0)


if __name__ == "__main__":
    main()
