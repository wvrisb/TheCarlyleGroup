"""Build the cleaned data model and event-attribution tables.

Run:  python src/build_model.py
Reads data/*.csv, writes output/*.csv. Every cleaning rule references a decision ID
(D1-D8) documented in docs/data_quality.md and docs/metric_definitions.md.
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA, OUT = ROOT / "data", ROOT / "output"
AS_OF = pd.Timestamp("2026-10-14")
WINDOWS = [30, 60, 90]
DEFAULT_WINDOW = 60
OUTLIER_OPPS = {"O0017"}            # D1: kept, but reportable with/without
LOW_CONF_OPPS = {"O9998"}           # D2: surviving record of the duplicated pair
DROP_OPPS = {"O9999"}               # D2: duplicate
STAGE_ORD = {"Initial Conversation": 1, "Follow-up / VDR": 2, "Due Diligence": 3,
             "IC / Documentation": 4, "Committed": 5, "Declined": 5}
SENIOR_TITLES = {"CIO", "Managing Director"}
ATT_DEFS = {"confirmed": "Any contact Confirmed",
            "incl_tentative": "Any contact Confirmed or Tentative"}


# --------------------------------------------------------------------------- load + clean
def load_raw():
    return dict(
        events=pd.read_csv(DATA / "events.csv", parse_dates=["event_date"]),
        firms=pd.read_csv(DATA / "firms.csv"),
        att=pd.read_csv(DATA / "event_attendees.csv"),
        meet=pd.read_csv(DATA / "meetings.csv", parse_dates=["meeting_date"]),
        opp=pd.read_csv(DATA / "opportunity_stage_history.csv",
                        parse_dates=["created_date", "stage_date"]),
    )


def build_dims_facts(raw):
    dim_event = raw["events"].copy()
    dim_firm = raw["firms"].copy()
    dim_firm["is_new_relationship"] = dim_firm.historical_commitments_usd.eq(0)

    # --- attendance (D4, D6): drop exact dup, drop unmapped, roll up to firm-event
    att = raw["att"].drop_duplicates().dropna(subset=["firm_id"]).copy()
    att["is_confirmed"] = att.attendance_status.eq("Confirmed")
    att["is_senior"] = att.contact_title.isin(SENIOR_TITLES)
    fact_attendance = (att.groupby(["event_id", "firm_id"])
                       .agg(contacts=("attendance_id", "count"),
                            confirmed_contacts=("is_confirmed", "sum"),
                            senior_contacts=("is_senior", "sum"),
                            cio_present=("contact_title", lambda s: (s == "CIO").any()))
                       .reset_index())
    fact_attendance["attendance_group"] = fact_attendance.confirmed_contacts.gt(0).map(
        {True: "Attended (Confirmed)", False: "Tentative only"})

    # --- meetings (D5): keep all rows, incl. same-day pair
    fact_meeting = raw["meet"].copy()

    # --- opportunity stages (D2, D3, D6)
    opp = raw["opp"][~raw["opp"].opportunity_id.isin(DROP_OPPS)].copy()
    future = opp[opp.stage_date > AS_OF]
    opp = opp[opp.stage_date <= AS_OF]
    opp["stage_ord"] = opp.stage.map(STAGE_ORD)
    # first date each stage was reached (D6: repeated IC rows collapse)
    fact_opp_stage = (opp.sort_values("stage_date")
                      .groupby(["opportunity_id", "stage"], as_index=False).first()
                      .sort_values(["opportunity_id", "stage_date"]))

    seq = fact_opp_stage.groupby("opportunity_id").stage.agg(list)
    last = fact_opp_stage.groupby("opportunity_id").last()
    dim_opp = (fact_opp_stage.groupby("opportunity_id")
               .agg(firm_id=("firm_id", "first"), fund_name=("fund_name", "first"),
                    created_date=("created_date", "first"),
                    amount_usd=("opportunity_amount_usd", "first"),
                    max_stage_ord=("stage_ord", "max"))
               .reset_index())
    dim_opp["current_stage"] = dim_opp.opportunity_id.map(last.stage)
    dim_opp["current_stage_date"] = dim_opp.opportunity_id.map(last.stage_date)
    dim_opp["flag_outlier"] = dim_opp.opportunity_id.isin(OUTLIER_OPPS)
    dim_opp["flag_low_confidence"] = dim_opp.opportunity_id.isin(LOW_CONF_OPPS)
    dim_opp["flag_skipped_diligence"] = dim_opp.opportunity_id.map(
        lambda o: "Committed" in seq[o] and "Due Diligence" not in seq[o])
    dim_opp["flag_future_stage_removed"] = dim_opp.opportunity_id.isin(future.opportunity_id)
    fact_opp_stage = fact_opp_stage.merge(
        dim_opp[["opportunity_id", "created_date"]].rename(columns={"created_date": "_c"}),
        on="opportunity_id").drop(columns="_c")
    return dict(dim_event=dim_event, dim_firm=dim_firm, fact_attendance=fact_attendance,
                fact_meeting=fact_meeting, fact_opp_stage=fact_opp_stage, dim_opportunity=dim_opp)


# --------------------------------------------------------------------------- attribution
def outcome_records(m):
    """One row per dated outcome, tagged with its type, firm, and dollars."""
    opp = m["dim_opportunity"]
    amt = opp.set_index("opportunity_id").amount_usd
    outl = opp.set_index("opportunity_id").flag_outlier
    meet = m["fact_meeting"].assign(type="meeting", date=lambda d: d.meeting_date,
                                    ref_id=lambda d: d.meeting_id, amount_usd=0.0)
    created = opp.assign(type="opp_created", date=opp.created_date, ref_id=opp.opportunity_id)
    st = m["fact_opp_stage"]
    reached = st[(st.stage_ord >= 2) & (st.stage != "Declined")]
    reached = reached.assign(type="stage_reached", date=reached.stage_date,
                             ref_id=reached.opportunity_id,
                             amount_usd=reached.opportunity_id.map(amt))
    commit = st[st.stage == "Committed"].assign(type="committed", date=lambda d: d.stage_date,
                                                ref_id=lambda d: d.opportunity_id,
                                                amount_usd=lambda d: d.opportunity_id.map(amt))
    cols = ["type", "firm_id", "date", "ref_id", "amount_usd"]
    rec = pd.concat([x[cols] for x in (meet, created, reached, commit)], ignore_index=True)
    rec["opp_created_date"] = rec.ref_id.map(opp.set_index("opportunity_id").created_date)
    rec["is_outlier"] = rec.ref_id.map(outl).fillna(False).astype(bool)
    return rec


def firm_event_outcomes(m):
    """One row per firm x event x window x attendance definition.

    in-window columns   : outcome counted if it falls in the window (multi-touch; any firm)
    *_lt columns        : last-touch -> credited only to the most recent attended event (D8)
    """
    ev, firms, fa = m["dim_event"], m["dim_firm"], m["fact_attendance"]
    rec = outcome_records(m)
    rows = []
    for att_def in ATT_DEFS:
        attended = fa if att_def == "incl_tentative" else fa[fa.confirmed_contacts > 0]
        att_set = set(zip(attended.event_id, attended.firm_id))
        ev_dates = ev.set_index("event_id").event_date
        for w in WINDOWS:
            # last-touch credit for every outcome
            def credit(r):
                cands = [(ev_dates[e], e) for (e, f) in att_set
                         if f == r.firm_id and ev_dates[e] <= r.date <= ev_dates[e] + pd.Timedelta(days=w)]
                return max(cands)[1] if cands else None
            rec_w = rec.copy()
            rec_w["credited_event"] = rec_w.apply(credit, axis=1)
            for _, e in ev.iterrows():
                d0 = e.event_date
                post = rec_w[(rec_w.date >= d0) & (rec_w.date <= d0 + pd.Timedelta(days=w))]
                pre = rec_w[(rec_w.date < d0) & (rec_w.date >= d0 - pd.Timedelta(days=w))]
                lt = rec_w[rec_w.credited_event == e.event_id]
                for f in firms.firm_id:
                    p, q, l = post[post.firm_id == f], pre[pre.firm_id == f], lt[lt.firm_id == f]
                    on_list = fa[(fa.event_id == e.event_id) & (fa.firm_id == f)]
                    group = ("Not on list" if on_list.empty else on_list.attendance_group.iloc[0])
                    pm = p[p.type == "meeting"]
                    adv = p[(p.type == "stage_reached") & (p.opp_created_date < d0)]
                    new = p[p.type == "opp_created"]
                    com = p[p.type == "committed"]
                    ladv = l[(l.type == "stage_reached") & (l.opp_created_date < d0)]
                    lnew, lcom = l[l.type == "opp_created"], l[l.type == "committed"]
                    ex = lambda df: df.loc[~df.is_outlier, "amount_usd"].sum()
                    rows.append(dict(
                        att_def=att_def, window_days=w, event_id=e.event_id, firm_id=f,
                        attendance_group=group, attended=(e.event_id, f) in att_set,
                        meetings_pre=int((q.type == "meeting").sum()),
                        meetings_post=len(pm),
                        days_to_first_meeting=(pm.date.min() - d0).days if len(pm) else None,
                        opps_created_pre=int((q.type == "opp_created").sum()),
                        opps_created_post=len(new), opps_created_post_usd=new.amount_usd.sum(),
                        opps_created_post_usd_ex=ex(new),
                        opps_advanced_post=adv.ref_id.nunique(),
                        opps_advanced_post_usd=adv.drop_duplicates("ref_id").amount_usd.sum(),
                        commits_post=len(com), commits_post_usd=com.amount_usd.sum(),
                        commits_post_usd_ex=ex(com),
                        # last-touch credited (attended firms only)
                        meetings_lt=int((l.type == "meeting").sum()),
                        opps_created_lt=len(lnew), opps_created_lt_usd=lnew.amount_usd.sum(),
                        opps_created_lt_usd_ex=ex(lnew),
                        opps_advanced_lt=ladv.ref_id.nunique(),
                        opps_advanced_lt_usd=ladv.drop_duplicates("ref_id").amount_usd.sum(),
                        commits_lt=len(lcom), commits_lt_usd=lcom.amount_usd.sum(),
                        commits_lt_usd_ex=ex(lcom),
                    ))
    return pd.DataFrame(rows)


def event_summary(feo, m):
    ev, firms = m["dim_event"], m["dim_firm"].set_index("firm_id")
    out = []
    for (att_def, w, e), g in feo.groupby(["att_def", "window_days", "event_id"]):
        a = g[g.attended]
        cost = ev.set_index("event_id").cost_usd[e]
        engaged = (a.meetings_post > 0).sum()
        out.append(dict(
            att_def=att_def, window_days=w, event_id=e, cost_usd=cost,
            firms_attended=len(a),
            tier1_firms=int((firms.loc[a.firm_id].priority == "Tier 1").sum()),
            firms_engaged=int(engaged),
            engagement_rate=engaged / len(a) if len(a) else None,
            median_days_to_first_meeting=a.days_to_first_meeting.median(),
            meetings_pre=int(a.meetings_pre.sum()), meetings_post=int(a.meetings_post.sum()),
            sourced_opps=int(a.opps_created_lt.sum()), sourced_usd=a.opps_created_lt_usd.sum(),
            influenced_opps=int(a.opps_advanced_lt.sum()), influenced_usd=a.opps_advanced_lt_usd.sum(),
            commits=int(a.commits_lt.sum()), commits_usd=a.commits_lt_usd.sum(),
            cost_per_attending_firm=cost / len(a) if len(a) else None,
            cost_per_engaged_firm=cost / engaged if engaged else None,
            sourced_usd_per_cost_usd=a.opps_created_lt_usd.sum() / cost,
        ))
    return pd.DataFrame(out)


def group_comparison(feo, m):
    """D11c: opportunity creation rate by attendance group within the post-event window."""
    firms = m["dim_firm"].set_index("firm_id")
    g = feo.assign(priority=feo.firm_id.map(firms.priority),
                   has_new_opp=feo.opps_created_post > 0)
    return (g.groupby(["att_def", "window_days", "event_id", "attendance_group", "priority"])
            .agg(firms=("firm_id", "count"), firms_with_new_opp=("has_new_opp", "sum"),
                 new_opps=("opps_created_post", "sum"), new_opp_usd=("opps_created_post_usd", "sum"))
            .reset_index())


def main():
    OUT.mkdir(exist_ok=True)
    m = build_dims_facts(load_raw())
    for name, df in m.items():
        df.to_csv(OUT / f"{name}.csv", index=False)
    feo = firm_event_outcomes(m)
    feo.to_csv(OUT / "firm_event_outcomes.csv", index=False)
    es = event_summary(feo, m)
    es.to_csv(OUT / "event_summary.csv", index=False)
    group_comparison(feo, m).to_csv(OUT / "group_comparison.csv", index=False)
    print("Wrote", sorted(p.name for p in OUT.glob("*.csv")))
    pd.set_option("display.width", 220, "display.max_columns", 40)
    print(es[(es.att_def == "confirmed") & (es.window_days == DEFAULT_WINDOW)].T)


if __name__ == "__main__":
    main()
