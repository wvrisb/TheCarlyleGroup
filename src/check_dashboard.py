"""Check that the dashboard's live calculations match src/analysis.py at default settings.

Run:  python src/check_dashboard.py      (needs: pip install playwright && playwright install chromium)
Opens dashboard/index.html headlessly, reads the figures the page computes, and
compares them with output/insights.json. Exits non-zero on any mismatch or page error.
"""
import json
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
ins = json.loads((ROOT / "output" / "insights.json").read_text())

JS = """() => ({
  fu: totals().fu / totals().att, base: share(attRows(), r => r.meetings_pre > 0),
  placebo: placebo(), did: didGroups(), live: liveFollow(), t1: tier1(), lag: lagStats(),
  attr: attribution(), calls: callList().length, callsP1: callList().filter(c => c.pr === 1).length,
  callsUsd: callList().reduce((s, c) => s + c.usd, 0), mix: eventVsMix(),
  t1_30: withWindow(30, tier1), t1_90: withWindow(90, tier1),
  inc: Object.fromEntries(EVS.map(e => { const x = eventStats(e); return [e, [x.extra, x.cpx]]; }))
})"""


def main():
    errors, fails = [], []
    with sync_playwright() as p:
        pg = p.chromium.launch().new_page()
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto((ROOT / "dashboard" / "index.html").as_uri())
        js = pg.evaluate(JS)
        for t in ["summary", "happened", "outcomes", "learn", "firms", "methods"]:
            for w in ["30", "60", "90"]:
                pg.click(f"#fWindow button[data-v='{w}']"); pg.click(f"nav.tabs button[data-tab={t}]")
    d = ins["60"]
    did = {r["group"]: r for r in d["new_deal_did"]}
    lf = d["live_deal_followup"]
    checks = [
        ("follow-up rate", js["fu"], d["followup_rate"]),
        ("baseline meeting rate", js["base"], d["baseline_meeting_rate"]),
        ("placebo attended pre/post", (js["placebo"]["att"]["pre"], js["placebo"]["att"]["post"]), (d["placebo_total"]["attended"]["pre"], d["placebo_total"]["attended"]["post"])),
        ("placebo other pre/post", (js["placebo"]["oth"]["pre"], js["placebo"]["oth"]["post"]), (d["placebo_total"]["other_event"]["pre"], d["placebo_total"]["other_event"]["post"])),
        ("new deals attended pre/post", (js["did"]["attended"]["pre"], js["did"]["attended"]["post"]), (did["attended"]["pre"], did["attended"]["post"])),
        ("new deals other-event pre/post", (js["did"]["other"]["pre"], js["did"]["other"]["post"]), (did["other_event"]["pre"], did["other_event"]["post"])),
        ("new deals never-invited pre/post", (js["did"]["never"]["pre"], js["did"]["never"]["post"]), (did["never_invited"]["pre"], did["never_invited"]["post"])),
        ("live deals followed up (n, rate)", (js["live"]["yN"], js["live"]["y"]), (lf["followed_up"]["n"], lf["followed_up"]["advanced_rate"])),
        ("live deals not followed up (n, rate)", (js["live"]["nN"], js["live"]["n"]), (lf["not_followed_up"]["n"], lf["not_followed_up"]["advanced_rate"])),
        ("Tier 1 missed firms", (js["t1"]["missFirms"], js["t1"]["firms"]), (d["tier1"]["missed_firms"], d["tier1"]["firms"])),
        ("Tier 1 missed firms @30d", js["t1_30"]["missFirms"], ins["30"]["tier1"]["missed_firms"]),
        ("Tier 1 missed firms @90d", js["t1_90"]["missFirms"], ins["90"]["tier1"]["missed_firms"]),
        ("first-meeting lag median", js["lag"]["med"], d["first_meeting_lag"]["median"]),
        ("attribution in >1 window", len(js["attr"]["multi"]), d["attribution"]["in_multiple_windows"]),
        ("attribution last-touch", js["attr"]["res"]["last"], d["attribution"]["by_rule"]["last"]),
        ("call list firms / P1 / $", (js["calls"], js["callsP1"], js["callsUsd"]), (d["call_list_summary"]["firms"], d["call_list_summary"]["priority1"], d["call_list_summary"]["live_usd"])),
        ("incremental follow-up (extra firms, cost per extra)", js["inc"], {e: [v["extra_firms"], v["cost_per_extra_firm"]] for e, v in d["incremental_followup"].items()}),
        ("event vs mix (London)", (js["mix"]["E002"]["actual"], js["mix"]["E002"]["expected"]), (d["event_vs_mix"]["E002"]["actual"], d["event_vs_mix"]["E002"]["expected_from_mix"])),
    ]
    norm = lambda v: json.dumps(v, sort_keys=True, default=lambda x: x) if not isinstance(v, (int, float, tuple, list)) else v
    for name, got, want in checks:
        ok = json.loads(json.dumps(got), parse_float=lambda x: round(float(x), 4)) == json.loads(json.dumps(want), parse_float=lambda x: round(float(x), 4))
        print(("OK   " if ok else "FAIL ") + name, "" if ok else f"dashboard={got} python={want}")
        if not ok: fails.append(name)
    print("page errors:", errors or "none")
    sys.exit(1 if fails or errors else 0)


if __name__ == "__main__":
    main()
