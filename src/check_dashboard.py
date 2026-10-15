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
  inc: Object.fromEntries(EVS.map(e => { const x = eventStats(e); return [e, [x.extra, x.cpx]]; })),
  season: Object.fromEntries(EVS.map(e => { const x = eventStats(e); return [e, [x.cN, x.exp, x.net, x.cpxNet]]; })),
  notMet: (c => [c.length, c.filter(x => x.od).length, c.reduce((s, x) => s + x.usd, 0), c.filter(x => x.od && x.f.priority === "Tier 1").length])(callList().filter(c => c.metSince == null)),
  speed: speedOutcome(), lg: loggingGap(), cmp: cmpFirmShare(), fa: followAttention(), who: whoCommits(), late: lateStage(), ex: existingMoved(),
  band: (() => { const g = k => oppsVisible().filter(o => oppGroup(o) === k && ageDays(o) >= MATURE_DAYS && ageDays(o) <= AGE_BAND_MAX);
    return Object.fromEntries([["event", "event"], ["before", "existing_before"]].map(([k, n]) => [n, [g(k).length, g(k).filter(o => o.current_stage === "Committed").length]])); })()
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
        ("placebo clean comparison pre/post", (js["placebo"]["oth"]["pre"], js["placebo"]["oth"]["post"]), (d["placebo_total"]["clean"]["pre"], d["placebo_total"]["clean"]["post"])),
        ("placebo original comparison pre/post", (js["placebo"]["othAll"]["pre"], js["placebo"]["othAll"]["post"]), (d["placebo_total"]["other_event_all"]["pre"], d["placebo_total"]["other_event_all"]["post"])),
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
        ("extra firms beyond the season (comparison n, expected, net, cost)", js["season"], {e: [v["comparison_firms"], v["seasonal_expected"], v["extra_beyond_season"], v["cost_per_extra_beyond_season"]] for e, v in d["incremental_followup"].items()}),
        ("call list: not met since (firms, with live deals, $, Tier 1 live)", js["notMet"], [d["call_list_summary"][k] for k in ("not_met_since", "not_met_since_live", "not_met_since_live_usd", "not_met_since_tier1_live")]),
        ("follow-up within 30 days vs later: n and new-deal rate", (js["speed"]["yN"], js["speed"]["yOpen"], js["speed"]["nN"], js["speed"]["nOpen"]),
         tuple(d["followup_speed_vs_outcome"][k][f] for k in ("within_30_days", "later_or_never") for f in ("n", "opened"))),
        ("logging gap (progressed firms, with no meetings)", (js["lg"]["n"], js["lg"]["none"]), (d["logging_gap"]["progressed_firms"], d["logging_gap"]["no_meetings"])),
        ("comparison firms met, counted in firms (n, before, after)", (js["cmp"]["n"], js["cmp"]["before"], js["cmp"]["after"]), (d["firm_share"]["clean"]["n"], d["firm_share"]["clean"]["before"], d["firm_share"]["clean"]["after"])),
        ("deals 120-240 days old: n and committed, event vs before", js["band"], {k: [d["age_matched_commit"][k]["n"], d["age_matched_commit"][k]["committed"]] for k in ("event", "existing_before")}),
        ("follow-up attention (team meetings after, with attendees, with earlier event's, solo before/after)", {e: [v["post"], v["toA"], v["toP"], v["soloPre"], v["soloPost"]] for e, v in js["fa"].items()},
         {e: [v["team_meetings_after"], v["with_attendees"], v["with_prior_event_attendees"], v["solo_pre"], v["solo_post"]] for e, v in d["followup_attention"].items()}),
        ("who commits: family offices vs others, incl. without fast commitments", [js["who"][k][f] for k in ("fo", "oth", "foNF", "othNF") for f in ("deals", "committed")],
         [d["who_commits"][k][f] for k in ("family_office", "others", "family_office_excl_fast", "others_excl_fast") for f in ("deals", "committed")]),
        ("who commits: places and committed $", [js["who"][k] for k in ("places", "placesFO", "placesInst", "usd", "usdFO", "usdInst")],
         [d["who_commits"][k] for k in ("places", "places_family_office", "places_found_ins_pension", "committed_usd", "committed_usd_family_office", "committed_usd_found_ins_pension")]),
        ("late-stage pipeline", [js["late"][k] for k in ("reached", "reachedCom", "reachedDec", "atIC", "atICusd", "atICfirms", "com", "skip", "comClean", "skipClean")],
         [d["late_stage"][k] for k in ("reached_ic", "reached_ic_committed", "reached_ic_declined", "at_ic_deals", "at_ic_usd", "at_ic_firms", "commitments", "commitments_skipping_dd", "commitments_clean", "commitments_clean_skipping_dd")]),
        ("existing deals moved forward: attended vs not at the event", (js["ex"]["attN"], js["ex"]["att"], js["ex"]["notN"], js["ex"]["not"]),
         (d["existing_deals_moved"]["attended"]["deals"], d["existing_deals_moved"]["attended"]["rate"], d["existing_deals_moved"]["not_at_event"]["deals"], d["existing_deals_moved"]["not_at_event"]["rate"])),
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
