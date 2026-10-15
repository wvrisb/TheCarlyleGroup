"""Insight analyses behind the dashboard narrative and the executive readout.

Run:  python src/build_model.py && python src/analysis.py
Reads output/*.csv (built by build_model.py) and writes output/insights.json.
Default settings: 60-day window, attended = any contact Confirmed. The dashboard
recomputes the same figures live for any filter; at default settings the two
must match (checked in src/check_dashboard.py).
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"
AS_OF = pd.Timestamp("2026-10-14")
AGE_BAND_MAX = 240
MATURE_DAYS = 120          # deals at least this old have had time to commit (median create->commit ~53d)
INSTITUTIONAL = {"Foundation", "Insurance"}  # Tier 1 pension funds were mostly followed up (3 of 4)


def load():
    r = lambda n, **k: pd.read_csv(OUT / f"{n}.csv", **k)
    return dict(
        ev=r("dim_event", parse_dates=["event_date"]).set_index("event_id"),
        firms=r("dim_firm").set_index("firm_id"),
        att=r("fact_attendance"),
        meet=r("fact_meeting", parse_dates=["meeting_date"]),
        opps=r("dim_opportunity", parse_dates=["created_date", "current_stage_date"]),
        stages=r("fact_opp_stage", parse_dates=["stage_date", "created_date"]),
        feo=r("firm_event_outcomes"),
    )


def analyse(m, w=60, att_def="confirmed"):
    ev, firms, att, meet, opps, stages, feo = (m[k] for k in ("ev", "firms", "att", "meet", "opps", "stages", "feo"))
    W = pd.Timedelta(days=w)
    attended = att if att_def == "incl_tentative" else att[att.confirmed_contacts > 0]
    pairs = set(zip(attended.event_id, attended.firm_id))
    ever, on_list = set(attended.firm_id), set(att.firm_id)
    f = feo[(feo.window_days == w) & (feo.att_def == att_def)].copy()
    a = f[f.attended].copy()
    a["tier"], a["seg"] = a.firm_id.map(firms.priority), a.firm_id.map(firms.segment)
    a["fu"] = a.meetings_post > 0
    out = {"window_days": w, "att_def": att_def}

    # 1. follow-up vs its own baseline
    out["followup_rate"] = a.fu.mean()
    out["baseline_meeting_rate"] = (a.meetings_pre > 0).mean()

    # 2. comparison group for seasonality: meetings around event X for firms that attended X vs firms that
    #    attended another event. "clean" = that firm had no attended event of its own within the window of X,
    #    so its own event's follow-up cannot inflate its "before" count. "overlap" = the rest (kept for the
    #    robustness note). The headline comparison uses attended vs clean.
    own = attended.assign(d=attended.event_id.map(ev.event_date)).groupby("firm_id").d.apply(list)
    rows = []
    for e in ev.index:
        d0 = ev.event_date[e]
        for fid in sorted(ever):
            mm = meet[meet.firm_id == fid].meeting_date
            if (e, fid) in pairs: grp = "attended"
            else: grp = "clean" if all(abs((x - d0).days) > w for x in own[fid]) else "overlap"
            rows.append(dict(event_id=e, firm_id=fid, group=grp, pre=int(((mm < d0) & (mm >= d0 - W)).sum()), post=int(((mm >= d0) & (mm <= d0 + W)).sum())))
    pl = pd.DataFrame(rows)
    out["placebo"] = pl.groupby(["event_id", "group"])[["pre", "post"]].sum().reset_index().to_dict("records")
    out["placebo_total"] = pl.groupby("group")[["pre", "post"]].sum().to_dict("index")
    tot = pl[pl.group != "attended"][["pre", "post"]].sum()
    out["placebo_total"]["other_event_all"] = {"pre": int(tot.pre), "post": int(tot.post)}   # original comparison, for the robustness note
    #    same comparison counted in firms: share of firm-event pairs with at least one meeting, before vs after
    out["firm_share"] = {g: dict(n=len(x), before=(x.pre > 0).mean(), after=(x.post > 0).mean())
                         for g, x in pl[pl.group.isin(["attended", "clean"])].groupby("group")}

    # 3. new-deal rate before vs after, by group (difference-in-differences)
    grp = lambda r: "attended" if r.attended else "other_event" if r.firm_id in ever else "never_invited" if r.firm_id not in on_list else "tentative_only"
    f["group"] = f.apply(grp, axis=1)
    g = f.groupby("group").agg(n=("firm_id", "size"), pre=("opps_created_pre", lambda s: (s > 0).mean()), post=("opps_created_post", lambda s: (s > 0).mean()))
    g["change"] = g.post - g.pre
    out["new_deal_did"] = g.reset_index().to_dict("records")

    # 4. follow-up vs deal movement, firms with a live deal at the event date
    def live(fid, d0):
        for _, o in opps[(opps.firm_id == fid) & (opps.created_date < d0)].iterrows():
            s = stages[stages.opportunity_id == o.opportunity_id]
            if not ((s.stage.isin(["Committed", "Declined"])) & (s.stage_date < d0)).any():
                return True
        return False
    a["live"] = [live(r.firm_id, ev.event_date[r.event_id]) for r in a.itertuples()]
    a["adv"] = a.opps_advanced_lt > 0
    lv = a[a.live].groupby("fu").adv.agg(["size", "mean"])
    out["live_deal_followup"] = {("followed_up" if k else "not_followed_up"): {"n": int(v["size"]), "advanced_rate": v["mean"]} for k, v in lv.iterrows()}

    # 5. Tier 1 follow-up (attendances and firms)
    t1 = a[a.tier == "Tier 1"]
    out["tier1"] = dict(attendances=len(t1), missed_attendances=int((~t1.fu).sum()),
                        firms=t1.firm_id.nunique(), missed_firms=t1[~t1.fu].firm_id.nunique())
    out["uninvited_tier1"] = sorted(set(firms[firms.priority == "Tier 1"].index) - on_list)

    # 6. segment: tier x institutional follow-up; event follow-up vs rate expected from its segment mix
    a["inst"] = a.seg.isin(INSTITUTIONAL)
    out["tier_by_institutional"] = a.groupby(["tier", "inst"]).fu.agg(["size", "mean"]).reset_index().to_dict("records")
    seg_rate = a.groupby("seg").fu.mean()
    out["event_vs_mix"] = {e: dict(actual=g_.fu.mean(), expected_from_mix=g_.seg.map(seg_rate).mean(), n=len(g_)) for e, g_ in a.groupby("event_id")}
    com = opps[opps.current_stage == "Committed"].assign(seg=lambda d: d.firm_id.map(firms.segment))
    out["commitments_by_segment"] = com.groupby("seg").amount_usd.agg(["count", "sum"]).reset_index().to_dict("records")

    # 7. window rationale: lag from event to first meeting (uncapped) for attended pairs
    lags = []
    for e, fid in pairs:
        d0, mm = ev.event_date[e], meet[(meet.firm_id == fid) & (meet.meeting_date >= ev.event_date[e])].meeting_date
        if len(mm): lags.append((mm.min() - d0).days)
    lags = pd.Series(lags)
    out["first_meeting_lag"] = dict(n=len(lags), of_pairs=len(pairs), median=lags.median(), within={k: (lags <= k).mean() for k in (30, 60, 90)})

    # 8. attribution robustness: new deals that fall in more than one attended window
    credit = {r: {e: 0.0 for e in ev.index} for r in ("last", "first", "split")}
    multi = 0
    for o in opps.itertuples():
        c = [e for e in ev.index if (e, o.firm_id) in pairs and ev.event_date[e] <= o.created_date <= ev.event_date[e] + W]
        if not c: continue
        multi += len(c) > 1
        c = sorted(c, key=lambda e: ev.event_date[e])
        credit["last"][c[-1]] += 1; credit["first"][c[0]] += 1
        for e in c: credit["split"][e] += 1 / len(c)
    out["attribution"] = dict(credited=sum(credit["last"].values()), in_multiple_windows=multi, by_rule=credit)

    # 9. funnel groups and mature-deal commit rate
    first_att = attended.assign(d=attended.event_id.map(ev.event_date)).groupby("firm_id").d.min()
    def origin(o):
        c = [e for e in ev.index if (e, o.firm_id) in pairs and ev.event_date[e] <= o.created_date <= ev.event_date[e] + W]
        if c: return "event"
        if o.firm_id not in ever: return "did_not_attend"
        return "existing_before" if o.created_date < first_att[o.firm_id] else "later_unlinked"
    opps = opps.assign(group=opps.apply(origin, axis=1), age=(AS_OF - opps.created_date).dt.days,
                       committed=opps.current_stage == "Committed")
    fg = opps.groupby("group").agg(n=("opportunity_id", "size"), committed=("committed", "sum"), median_age=("age", "median"))
    mat = opps[opps.age >= MATURE_DAYS].groupby("group").agg(mature_n=("committed", "size"), mature_commit_rate=("committed", "mean"))
    out["funnel_groups"] = fg.join(mat).reset_index().to_dict("records")
    #    deals already open before a firm's first event are older on average; compare deals of similar age
    #    (120-240 days old, the range where both groups overlap) so age does not drive the gap
    band = opps[(opps.age >= MATURE_DAYS) & (opps.age <= AGE_BAND_MAX)]
    out["age_matched_commit"] = {g: dict(n=len(x), committed=int(x.committed.sum()), rate=x.committed.mean())
                                 for g, x in band.groupby("group")}
    out["median_age"] = {g: float(x.age.median()) for g, x in opps.groupby("group")}

    # 10. priority call list: attending firms with no follow-up, ranked by live deals
    gap = a[~a.fu]
    open_ = opps[~opps.current_stage.isin(["Committed", "Declined"])]
    calls = []
    for fid, gg in gap.groupby("firm_id"):
        od = open_[open_.firm_id == fid]
        top = int(od.max_stage_ord.max()) if len(od) else 0
        pr = 1 if top >= 3 else 2 if (len(od) or firms.priority[fid] == "Tier 1") else 3
        last_ev = max(ev.event_date[e] for e in gg.event_id)
        since = meet[(meet.firm_id == fid) & (meet.meeting_date > last_ev)].meeting_date
        calls.append(dict(firm_id=fid, tier=firms.priority[fid], segment=firms.segment[fid], events=sorted(gg.event_id),
                          open_deals=len(od), open_usd=float(od.amount_usd.sum()), furthest_stage_ord=top, priority=pr,
                          met_since=since.min().strftime("%Y-%m-%d") if len(since) else None))
    # firms with no logged meeting since their event come first: those are the ones to call; "met later" firms
    # show slow follow-up but have since been met
    calls = sorted(calls, key=lambda c: (c["met_since"] is not None, c["priority"], c["tier"], -c["open_usd"]))
    out["call_list"] = calls
    out["call_list_summary"] = dict(firms=len(calls), with_live_deals=sum(c["open_deals"] > 0 for c in calls),
                                    live_usd=sum(c["open_usd"] for c in calls), priority1=sum(c["priority"] == 1 for c in calls))
    ns = [c for c in calls if c["met_since"] is None]
    out["call_list_summary"].update(not_met_since=len(ns), not_met_since_live=sum(c["open_deals"] > 0 for c in ns),
                                    not_met_since_live_usd=sum(c["open_usd"] for c in ns),
                                    not_met_since_tier1_live=sum(c["open_deals"] > 0 and c["tier"] == "Tier 1" for c in ns),
                                    met_later=len(calls) - len(ns))

    # 11. incremental follow-up: extra attending firms met after vs before, and event cost per extra firm
    #     "beyond the season": subtract the extra firms the comparison group's change in share-met implies
    #     (attending firms x (comparison share met after - share met before)); needs >= 5 comparison firms.
    inc = {}
    for e, g_ in a.groupby("event_id"):
        extra = int((g_.meetings_post > 0).sum() - (g_.meetings_pre > 0).sum())
        c_ = pl[(pl.event_id == e) & (pl.group == "clean")]
        exp_ = len(g_) * ((c_.post > 0).mean() - (c_.pre > 0).mean()) if len(c_) >= 5 else None
        net = extra - exp_ if exp_ is not None else None
        inc[e] = dict(met_after=int((g_.meetings_post > 0).sum()), met_before=int((g_.meetings_pre > 0).sum()), extra_firms=extra,
                      cost_per_extra_firm=float(ev.cost_usd[e] / extra) if extra > 0 else None,
                      comparison_firms=len(c_), comparison_share_before=(c_.pre > 0).mean(), comparison_share_after=(c_.post > 0).mean(),
                      seasonal_expected=exp_, extra_beyond_season=net,
                      cost_per_extra_beyond_season=float(ev.cost_usd[e] / net) if net is not None and net >= 1 else None)
    out["incremental_followup"] = inc

    # 13. does faster follow-up go with better deal outcomes? (association only)
    a["fu_fast"] = a.days_to_first_meeting.le(30)
    out["followup_speed_vs_outcome"] = {("within_30_days" if k else "later_or_never"): dict(n=len(g_), opened=(g_.opps_created_post > 0).mean(),
                                         advanced=(g_.opps_advanced_post > 0).mean()) for k, g_ in a.groupby("fu_fast")}

    # 14. logging gap: attending firms whose deal moved past the first stage but with no meeting logged at all
    progressed = set(stages[stages.stage_ord >= 2].firm_id) & ever
    out["logging_gap"] = dict(progressed_firms=len(progressed), no_meetings=len(progressed - set(meet.firm_id)),
                              firms=sorted(progressed - set(meet.firm_id)))

    # 15. follow-up attention after each event: team meetings in the window after, and how many went to that
    #     event's attendees; and attendees with no other attended event in the window before (no overlap)
    att_by_e = attended.groupby("event_id").firm_id.apply(set)
    focus = {}
    for e in ev.index:
        d0 = ev.event_date[e]
        post_m = meet[(meet.meeting_date >= d0) & (meet.meeting_date <= d0 + W)]
        to_att = post_m[post_m.firm_id.isin(att_by_e[e])]
        prior = {x for x in ev.index if x != e and d0 - W <= ev.event_date[x] < d0}
        solo = [fid for fid in att_by_e[e] if not any(fid in att_by_e[x] for x in prior)]
        s_ = a[(a.event_id == e) & a.firm_id.isin(solo)]
        focus[e] = dict(team_meetings_after=len(post_m), with_attendees=len(to_att),
                        by_team={t: [int((post_m.internal_attendee == t).sum()), int((to_att.internal_attendee == t).sum())]
                                 for t in sorted(meet.internal_attendee.unique())},
                        with_prior_event_attendees=int(post_m[~post_m.firm_id.isin(att_by_e[e]) & post_m.firm_id.isin(set().union(*[att_by_e[x] for x in prior]))].shape[0]) if prior else 0,
                        solo_firms=len(solo), solo_pre=int(s_.meetings_pre.sum()), solo_post=int(s_.meetings_post.sum()))
    out["followup_attention"] = focus

    # 12. uncertainty: bootstrap 95% ranges (resampling firm-event pairs, 5,000 draws, fixed seed)
    rng = np.random.default_rng(7)
    A, O = pl[pl.group == "attended"][["pre", "post"]].values, pl[pl.group == "clean"][["pre", "post"]].values
    def growth_gap(a_, o_):
        return a_[:, 1].sum() / a_[:, 0].sum() - o_[:, 1].sum() / o_[:, 0].sum() if a_[:, 0].sum() and o_[:, 0].sum() else np.nan
    draws = [growth_gap(A[rng.integers(0, len(A), len(A))], O[rng.integers(0, len(O), len(O))]) for _ in range(5000)]
    out["ci_meeting_growth_gap"] = dict(point=growth_gap(A, O), lo=float(np.nanpercentile(draws, 2.5)), hi=float(np.nanpercentile(draws, 97.5)))
    Ad = f[f.group == "attended"][["opps_created_pre", "opps_created_post"]].gt(0).values.astype(int)
    Od = f[f.group == "other_event"][["opps_created_pre", "opps_created_post"]].gt(0).values.astype(int)
    did = lambda a_, o_: (a_[:, 1].mean() - a_[:, 0].mean()) - (o_[:, 1].mean() - o_[:, 0].mean())
    draws = [did(Ad[rng.integers(0, len(Ad), len(Ad))], Od[rng.integers(0, len(Od), len(Od))]) for _ in range(5000)]
    out["ci_new_deal_gap"] = dict(point=did(Ad, Od), lo=float(np.percentile(draws, 2.5)), hi=float(np.percentile(draws, 97.5)))
    return out


def main():
    m = load()
    res = {w: analyse(m, w) for w in (30, 60, 90)}
    (OUT / "insights.json").write_text(json.dumps(res, indent=1, default=float))
    d = res[60]
    print(f"Follow-up {d['followup_rate']:.0%} vs baseline {d['baseline_meeting_rate']:.0%}")
    print("Placebo totals:", d["placebo_total"])
    print("New-deal before/after:", [(r['group'], round(r['pre'], 2), round(r['post'], 2), r['n']) for r in d["new_deal_did"]])
    print("Live-deal follow-up:", d["live_deal_followup"])
    print("Tier 1:", d["tier1"], "| uninvited Tier 1:", d["uninvited_tier1"])
    print("Event vs mix:", {k: (round(v['actual'], 2), round(v['expected_from_mix'], 2)) for k, v in d["event_vs_mix"].items()})
    print("Lag:", d["first_meeting_lag"])
    print("Attribution:", d["attribution"])
    print("Funnel groups:", d["funnel_groups"])
    print("Call list:", d["call_list_summary"])
    print("Follow-up speed vs outcome:", d["followup_speed_vs_outcome"])
    print("Logging gap:", d["logging_gap"])
    print("Incremental follow-up:", d["incremental_followup"])
    print("95% range, meeting growth gap:", {k: round(v, 2) for k, v in d["ci_meeting_growth_gap"].items()})
    print("95% range, new-deal gap:", {k: round(v, 2) for k, v in d["ci_new_deal_gap"].items()})
    for w in (30, 90):
        print(f"[{w}d] follow-up {res[w]['followup_rate']:.0%}, Tier 1 missed firms {res[w]['tier1']['missed_firms']}/{res[w]['tier1']['firms']}")


if __name__ == "__main__":
    main()
